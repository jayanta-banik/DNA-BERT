import { parseDirectoryLinks } from '#util/web_scrapper';
import cliProgress from 'cli-progress';
import got from 'got';
import fs from 'node:fs/promises';
import path from 'node:path';
import pLimit from 'p-limit';

const INPUT_JSONL_PATH = 'results/ncbi_bacteria_directory.jsonl';
const OUTPUT_JSONL_PATH = 'results/ncbi_bacteria_tree.jsonl';
const REQUEST_TIMEOUT_MS = 30000;

const RED = '\x1b[31m';
const WHITE = '\x1b[37m';
const RESET = '\x1b[0m';

const CONCURRENCY = Number(process.env.CONCURRENCY ?? 15);
const limit = pLimit(CONCURRENCY);

const progressBar = new cliProgress.SingleBar(
  {
    format: '{statusColor}tree [{bar}] {value}/{total} rows' + RESET,
    hideCursor: true,
    clearOnComplete: true,
  },
  cliProgress.Presets.shades_classic,
);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readJsonlRows(filePath) {
  try {
    const text = await fs.readFile(filePath, 'utf8');
    const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);

    return lines.map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (e) {
        throw new Error(`Invalid JSON at ${filePath}:${index + 1}`);
      }
    });
  } catch (e) {
    // If output doesn't exist yet, treat as empty
    if (e && typeof e === 'object' && 'code' in e && e.code === 'ENOENT') return [];
    throw e;
  }
}

async function readInputRows() {
  const rows = await readJsonlRows(INPUT_JSONL_PATH);

  return rows.map((row, index) => {
    if (!row?.source_url) {
      throw new Error(`Missing source_url at input line ${index + 1}`);
    }
    return row;
  });
}

async function fetchSubDirs(sourceUrl) {
  const response = await got(sourceUrl, {
    timeout: { request: REQUEST_TIMEOUT_MS },
    retry: { limit: 5 },
    throwHttpErrors: true,
  });

  const links = parseDirectoryLinks({ html: response.body, pageUrl: sourceUrl });
  return links.map((link) => ({
    bacteria_name: link.label,
    source_url: link.url,
    is_dir: link.isDirectory,
  }));
}

function prettyPathFromUrl(url) {
  const idx = url.indexOf('/bacteria/');
  return idx >= 0 ? url.slice(idx + '/bacteria/'.length) : url;
}

async function processRow(row) {
  let outRow;
  let color = WHITE;

  try {
    const subDirs = await fetchSubDirs(row.source_url);

    outRow = {
      bacteria_name: row.bacteria_name ?? null,
      source_url: row.source_url,
      is_dir: row.is_dir ?? null,
      sub_dirs: subDirs,
      status: 'done',
    };

    color = WHITE;
  } catch (err) {
    const status = err?.response?.statusCode;
    const code = err?.code;
    const msg = err?.message ?? String(err);

    console.error(`Failed: ${prettyPathFromUrl(row.source_url)} status=${status ?? '-'} code=${code ?? '-'} msg=${msg}`);
    // await sleep(1000); // Small delay to avoid overwhelming console if many errors

    if (process.env.DEBUG_ERRORS === '1') {
      console.error(err?.response?.body?.slice?.(0, 200));
    }
    outRow = {
      bacteria_name: row.bacteria_name ?? null,
      source_url: row.source_url,
      is_dir: row.is_dir ?? null,
      sub_dirs: [],
      status: 'failed',
    };

    color = RED;
    console.error(`Failed: ${prettyPathFromUrl(row.source_url)} (${row.source_url})`);
    if (process.env.DEBUG_ERRORS === '1') {
      console.error(err instanceof Error ? err.stack : String(err));
    }
  }

  // Append is safe with concurrent tasks on POSIX for small lines; still, keep each write a single append.
  await fs.appendFile(OUTPUT_JSONL_PATH, `${JSON.stringify(outRow)}\n`, 'utf8');

  progressBar.increment(1, { statusColor: color });
}

async function rebuildOutputKeepingOnlyDone() {
  const existing = await readJsonlRows(OUTPUT_JSONL_PATH);

  // Keep ONLY latest "done" per source_url (and drop all failed)
  const doneByUrl = new Map();
  for (const row of existing) {
    if (row?.source_url && row?.status === 'done') {
      doneByUrl.set(row.source_url, row);
    }
  }

  const kept = [...doneByUrl.values()];
  const tmpPath = `${OUTPUT_JSONL_PATH}.tmp`;

  await fs.mkdir(path.dirname(OUTPUT_JSONL_PATH), { recursive: true });
  await fs.writeFile(tmpPath, kept.map((r) => `${JSON.stringify(r)}\n`).join(''), 'utf8');
  await fs.rename(tmpPath, OUTPUT_JSONL_PATH);

  return doneByUrl; // Map(source_url -> doneRow)
}

async function run() {
  await fs.mkdir(path.dirname(OUTPUT_JSONL_PATH), { recursive: true });

  // 1) Clean/resume: keep only "done" rows in output; delete failed rows
  const doneByUrl = await rebuildOutputKeepingOnlyDone();

  // 2) Read input and skip anything already done
  const inputRows = await readInputRows();
  const pendingRows = inputRows.filter((r) => !doneByUrl.has(r.source_url));

  progressBar.start(inputRows.length, inputRows.length - pendingRows.length, { statusColor: WHITE });

  // await Promise.all(pendingRows.map((row) => limit(() => processRow(row))));
  for (const row of pendingRows) {
    await processRow(row);
  }

  progressBar.stop();

  console.log(`Saved ${pendingRows.length} new rows to ${OUTPUT_JSONL_PATH} (skipped ${inputRows.length - pendingRows.length} already done)`);
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
