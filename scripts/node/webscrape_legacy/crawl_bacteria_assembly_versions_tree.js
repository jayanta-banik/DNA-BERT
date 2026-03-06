import cliProgress from 'cli-progress';
import fs from 'node:fs/promises';
import path from 'node:path';
import pLimit from 'p-limit';

import { readJSONL, writeJSONL } from '#util/jsonl_store';
import { fetchWithRetry, parseDirectoryLinks } from '#util/web_scrapper';

const INPUT_JSONL_PATH = 'results/latest_assembly_bacteria_tree.jsonl';
const OUTPUT_JSONL_PATH = 'results/bacteria_assembly_version_tree.jsonl';
const WARNING_LOG_FILE = 'results/files_warning.jsonl';
const OUTPUT_PATH = 'data/raw/';
const CONCURRENCY = 5;

const RED = '\x1b[31m';
const WHITE = '\x1b[37m';
const RESET = '\x1b[0m';

const progressBar = new cliProgress.SingleBar(
  {
    format: '{statusColor}tree [{bar}] {value}/{total} rows' + RESET,
    hideCursor: true,
    clearOnComplete: true,
  },
  cliProgress.Presets.shades_classic,
);

const limit = pLimit(CONCURRENCY);

async function processRow(row) {
  let color = WHITE;

  try {
    const data = await fetchWithRetry({ sourceUrl: row.source_url });
    const links = parseDirectoryLinks({ html: data.body, pageUrl: row.source_url });

    const outRow = {
      bacteria_name: row.bacteria_name,
      source_url: row.source_url,
      status: 'done',
      sub_dirs: links.map((link) => ({
        dir_name: link.label,
        source_url: link.url,
        is_dir: link.isDirectory,
      })),
    };

    // keep append immediate so crash recovery still works
    await fs.appendFile(OUTPUT_JSONL_PATH, `${JSON.stringify(outRow)}\n`, 'utf8');
  } catch (err) {
    color = RED;

    const status = err?.response?.statusCode;
    const msg = err?.message ?? String(err);
    const code = err?.code ?? '-';

    console.error(`Failed: ${row.source_url} status=${status ?? '-'} code=${code} msg=${msg}`);

    // optional warning log for later retry/debug
    await fs
      .appendFile(
        WARNING_LOG_FILE,
        `${JSON.stringify({
          bacteria_name: row.bacteria_name,
          source_url: row.source_url,
          status: 'failed',
          http_status: status ?? null,
          error_code: code,
          error_message: msg,
        })}\n`,
        'utf8',
      )
      .catch(() => {
        // don't let warning log failure break the main pipeline
      });
  } finally {
    progressBar.increment(1, { statusColor: color });
  }
}

async function run() {
  await fs.mkdir(path.dirname(OUTPUT_JSONL_PATH), { recursive: true });
  await fs.mkdir(path.dirname(WARNING_LOG_FILE), { recursive: true });

  // recover output file: keep only rows already marked done
  const cachedOutputRows = await readJSONL({
    filePath: OUTPUT_JSONL_PATH,
    ignoreMissing: true,
  });

  const doneRows = cachedOutputRows.filter((r) => r.status === 'done');
  await writeJSONL({ filePath: OUTPUT_JSONL_PATH, rows: doneRows });

  const doneByUrl = new Set(doneRows.map((r) => r.source_url));

  // read input and skip completed rows
  const inputRows = await readJSONL({ filePath: INPUT_JSONL_PATH });
  const pendingRows = inputRows.filter((r) => !doneByUrl.has(r.source_url));

  progressBar.start(inputRows.length, inputRows.length - pendingRows.length, {
    statusColor: WHITE,
  });

  await Promise.all(pendingRows.map((row) => limit(() => processRow(row))));

  progressBar.stop();

  console.log(`Saved ${pendingRows.length} new rows to ${OUTPUT_JSONL_PATH} (skipped ${inputRows.length - pendingRows.length} already done)`);
}

await run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
