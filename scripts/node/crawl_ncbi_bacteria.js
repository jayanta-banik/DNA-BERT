import cliProgress from 'cli-progress';
import got from 'got';
import { createWriteStream } from 'node:fs';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pipeline } from 'node:stream/promises';
import pLimit from 'p-limit';

import { parseDirectoryLinks, splitVersionEntries } from '#util/index_parser';
import { appendSummaryRow, createSummaryRow, loadPriorSummaryMap, validateSummaryRowsAgainstSchema } from '#util/jsonl_store';
import { buildLatestAssemblyUrl, buildRowKey, clearRowOutput, ensureDirectory, hasConsistentOutput, mapRemotePathToLocal, sanitizeBacteriaName } from '#util/path_utils';

const CSV_FILE_PATH = process.env.CSV_FILE_PATH ?? 'data/external/bacteria_index.csv';
const OUTPUT_JSONL_PATH = process.env.OUTPUT_JSONL_PATH ?? 'results/ncbi_bacteria_links.jsonl';
const OUTPUT_FOLDER_PATH = process.env.OUTPUT_FOLDER_PATH ?? 'data/raw/genbank/bacteria';
const JSON_SCHEMA_PATH = process.env.JSON_SCHEMA_PATH ?? 'specs/001-ncbi-bacteria-crawler/contracts/jsonl-summary.schema.json';
// const CONCURRENCY = Number(process.env.CONCURRENCY ?? 15);
const CONCURRENCY = 5;
const REQUEST_TIMEOUT_MS = 30000;

function parseCsvLine({ line } = {}) {
  const cells = [];
  let currentCell = '';
  let isQuoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];

    if (char === '"') {
      const escapedQuote = isQuoted && line[index + 1] === '"';
      if (escapedQuote) {
        currentCell += '"';
        index += 1;
      } else {
        isQuoted = !isQuoted;
      }
      continue;
    }

    if (char === ',' && !isQuoted) {
      cells.push(currentCell);
      currentCell = '';
      continue;
    }

    currentCell += char;
  }

  cells.push(currentCell);
  return cells.map((cell) => cell.trim());
}

async function readInputRows({ csvFilePath } = {}) {
  const csvBuffer = await fs.readFile(csvFilePath);
  const csvText = csvBuffer.toString('utf8');

  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim().length > 0);

  const headerCells = parseCsvLine({ line: lines[0] });
  if (headerCells.length !== 2 || headerCells[0] !== 'bacteria_name' || headerCells[1] !== 'url') {
    throw new Error('CSV header must be exactly: bacteria_name,url');
  }

  const inputRows = [];

  for (let lineIndex = 1; lineIndex < lines.length; lineIndex += 1) {
    const rowNumber = lineIndex + 1;
    const cells = parseCsvLine({ line: lines[lineIndex] });

    const bacteriaName = cells[0];
    const sourceUrl = cells[1];

    inputRows.push({
      row_index: rowNumber,
      bacteria_name: bacteriaName,
      source_url: sourceUrl,
    });
  }

  return inputRows;
}

async function fetchDirectoryLinks({ directoryUrl } = {}) {
  const response = await got(directoryUrl, {
    headers: REQUEST_HEADERS,
    timeout: { request: REQUEST_TIMEOUT_MS },
    retry: { limit: 0 },
    throwHttpErrors: true,
  });

  return parseDirectoryLinks({ html: response.body, pageUrl: directoryUrl });
}

async function downloadFile({ fileUrl, latestAssemblyRootUrl, bacteriaOutputDir } = {}) {
  const outputPath = mapRemotePathToLocal({
    latestAssemblyRootUrl,
    fileUrl,
    bacteriaOutputDir,
  });

  await ensureDirectory({ dirPath: path.dirname(outputPath) });

  const readStream = got.stream(fileUrl, {
    headers: REQUEST_HEADERS,
    timeout: { request: REQUEST_TIMEOUT_MS },
    retry: { limit: 0 },
  });

  const writeStream = createWriteStream(outputPath);
  await pipeline(readStream, writeStream);
}

async function crawlAndDownload({ currentUrl, latestAssemblyRootUrl, bacteriaOutputDir, visitedDirectories } = {}) {
  if (visitedDirectories.has(currentUrl)) {
    return 0;
  }

  visitedDirectories.add(currentUrl);
  const links = await fetchDirectoryLinks({ directoryUrl: currentUrl });

  let downloadedCount = 0;

  for (const link of links) {
    if (link.isDirectory) {
      downloadedCount += await crawlAndDownload({
        currentUrl: link.url,
        latestAssemblyRootUrl,
        bacteriaOutputDir,
        visitedDirectories,
      });
      continue;
    }

    await downloadFile({
      fileUrl: link.url,
      latestAssemblyRootUrl,
      bacteriaOutputDir,
    });
    downloadedCount += 1;
  }

  return downloadedCount;
}

async function processRow({ row, priorSummaryMap, outputFolderPath } = {}) {
  const bacteriaName = row.bacteria_name;
  const sourceUrl = row.source_url;
  const rowKey = buildRowKey({ bacteriaName, sourceUrl });
  const priorSummary = priorSummaryMap.get(rowKey);
  const safeBacteriaName = sanitizeBacteriaName({ bacteriaName });
  const bacteriaOutputDir = path.join(outputFolderPath, safeBacteriaName);

  if (priorSummary?.download_completed) {
    const consistentOutput = await hasConsistentOutput({
      bacteriaOutputDir,
      expectedDownloadedFileCount: priorSummary.downloaded_file_count,
    });

    if (consistentOutput) {
      return createSummaryRow({
        bacteriaName,
        sourceUrl,
        latestAssemblyVersionsAvailable: priorSummary.latest_assembly_versions_available,
        discoveredVersionCount: priorSummary.discovered_version_count,
        downloadedFileCount: priorSummary.downloaded_file_count,
        downloadCompleted: true,
        versions: priorSummary.versions ?? [],
        status: priorSummary.status,
        errorMessage: priorSummary.error_message,
      });
    }
  }

  await clearRowOutput({ bacteriaOutputDir });

  const latestAssemblyVersionsUrl = buildLatestAssemblyUrl({ sourceUrl });
  let rootLinks;

  try {
    rootLinks = await fetchDirectoryLinks({ directoryUrl: latestAssemblyVersionsUrl });
  } catch (error) {
    const statusCode = error?.response?.statusCode;
    if (statusCode === 404 || statusCode === 403) {
      return createSummaryRow({
        bacteriaName,
        sourceUrl,
        latestAssemblyVersionsAvailable: false,
        discoveredVersionCount: 0,
        downloadedFileCount: 0,
        downloadCompleted: false,
        versions: [],
        status: 'skipped',
      });
    }

    throw error;
  }

  await ensureDirectory({ dirPath: bacteriaOutputDir });

  const versions = splitVersionEntries({ links: rootLinks });
  const visitedDirectories = new Set();
  const downloadedFileCount = await crawlAndDownload({
    currentUrl: latestAssemblyVersionsUrl,
    latestAssemblyRootUrl: latestAssemblyVersionsUrl,
    bacteriaOutputDir,
    visitedDirectories,
  });

  return createSummaryRow({
    bacteriaName,
    sourceUrl,
    latestAssemblyVersionsAvailable: true,
    discoveredVersionCount: versions.length,
    downloadedFileCount,
    downloadCompleted: true,
    versions,
    status: 'success',
  });
}

async function run() {
  await ensureDirectory({ dirPath: path.dirname(OUTPUT_JSONL_PATH) });
  await ensureDirectory({ dirPath: OUTPUT_FOLDER_PATH });

  const inputRows = await readInputRows({ csvFilePath: CSV_FILE_PATH });
  const priorSummaryMap = await loadPriorSummaryMap({ outFilePath: OUTPUT_JSONL_PATH });

  // Clear JSONL file for fresh run (maintains one-record-per-input-row invariant)
  await fs.writeFile(OUTPUT_JSONL_PATH, '', 'utf8');

  const limiter = pLimit(CONCURRENCY);
  const summaryRows = new Array(inputRows.length);
  const progressBar = new cliProgress.SingleBar(
    {
      format: 'crawl [{bar}] {value}/{total} rows',
      hideCursor: true,
      clearOnComplete: true,
    },
    cliProgress.Presets.shades_classic,
  );

  progressBar.start(inputRows.length, 0);

  const tasks = inputRows.map((row, index) =>
    limiter(async () => {
      //   console.log(`[row:${row.row_index}] start ${row.bacteria_name}`);

      try {
        const summaryRow = await processRow({
          row,
          priorSummaryMap,
          outputFolderPath: OUTPUT_FOLDER_PATH,
        });

        summaryRows[index] = summaryRow;

        // Save progress incrementally to enable crash recovery
        await appendSummaryRow({
          outFilePath: OUTPUT_JSONL_PATH,
          summaryRow,
        });

        // console.log(`[row:${row.row_index}] done status=${summaryRow.status}`);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        const summaryRow = createSummaryRow({
          bacteriaName: row.bacteria_name,
          sourceUrl: row.source_url,
          latestAssemblyVersionsAvailable: false,
          discoveredVersionCount: 0,
          downloadedFileCount: 0,
          downloadCompleted: false,
          versions: [],
          status: 'failed',
          errorMessage,
        });

        summaryRows[index] = summaryRow;

        // Save failed row immediately for reconciliation on next run
        await appendSummaryRow({
          outFilePath: OUTPUT_JSONL_PATH,
          summaryRow,
        });

        console.error(`[row:${row.row_index}] failed ${errorMessage}`);
      } finally {
        progressBar.increment();
      }
    }),
  );

  await Promise.all(tasks);
  progressBar.stop();

  await validateSummaryRowsAgainstSchema({
    schemaPath: JSON_SCHEMA_PATH,
    summaryRows,
  });

  //   console.log(`Wrote ${summaryRows.length} summary rows to ${OUTPUT_JSONL_PATH}`);
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
