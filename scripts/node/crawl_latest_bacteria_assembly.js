import cliProgress from 'cli-progress';
import fs from 'node:fs/promises';
import path from 'node:path';

import { readJSONL, writeJSONL } from '#util/jsonl_store';
import { fetchWithRetry, parseDirectoryLinks } from '#util/web_scrapper';

const INPUT_JSONL_PATH = 'results/latest_assembly_versions.jsonl';
const OUTPUT_JSONL_PATH = 'results/latest_assembly_bacteria_tree.jsonl';

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

async function processRow(row) {
  let outRows;
  let color = WHITE;

  try {
    const data = await fetchWithRetry({ sourceUrl: row.source_url });

    const links = parseDirectoryLinks({ html: data.body, pageUrl: row.source_url });

    outRows = links.map((link) => ({
      bacteria_name: row.bacteria_name,
      dir_name: link.label,
      source_url: link.url,
      is_dir: link.isDirectory,
      status: 'done',
    }));
    // Append is safe with concurrent tasks on POSIX for small lines; still, keep each write a single append.
    for (const outRow of outRows) {
      await fs.appendFile(OUTPUT_JSONL_PATH, `${JSON.stringify(outRow)}\n`, 'utf8');
    }
  } catch (err) {
    color = RED;
    const status = err?.response?.statusCode;
    const msg = err?.message ?? String(err);

    console.error(`Failed: ${row.source_url} status=${status ?? '-'} code=${err?.code ?? '-'} msg=${msg}`);
  }

  progressBar.increment(1, { statusColor: color });
}

async function run() {
  await fs.mkdir(path.dirname(OUTPUT_JSONL_PATH), { recursive: true });

  // read cached JSONL output if exists, clean and keep only "done" rows, and build a map of done source_urls to skip in input
  const cachedOutputRows = await readJSONL({ filePath: OUTPUT_JSONL_PATH, ignoreMissing: true });
  const doneRows = cachedOutputRows.filter((r) => r.status === 'done');
  await writeJSONL({ filePath: OUTPUT_JSONL_PATH, rows: doneRows });
  const doneByUrl = new Set(doneRows.map((r) => r.source_url));

  // 2) Read input and skip anything already done
  const inputRows = await readJSONL({ filePath: INPUT_JSONL_PATH });
  const pendingRows = inputRows.filter((r) => !doneByUrl.has(r.source_url));

  progressBar.start(inputRows.length, inputRows.length - pendingRows.length, { statusColor: WHITE });

  for (const row of pendingRows) {
    await processRow(row);
  }

  progressBar.stop();

  console.log(`Saved ${pendingRows.length} new rows to ${OUTPUT_JSONL_PATH} (skipped ${inputRows.length - pendingRows.length} already done)`);
}

await run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
