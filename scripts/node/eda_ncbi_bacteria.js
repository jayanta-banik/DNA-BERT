import { load } from 'cheerio';
import cliProgress from 'cli-progress';
import fs from 'node:fs/promises';
import path from 'node:path';

const LISTING_HTML_FILE = 'file:///home/ubuntu/projects/biodata/DNA-BERT/data/external/Index_of_genomes_genbank_bacteria.html';
const NCBI_BACTERIA_BASE_URL = 'https://ftp.ncbi.nlm.nih.gov/genomes/genbank/bacteria/';
const OUTPUT_JSONL_PATH = 'results/ncbi_bacteria_directory.jsonl';

async function ensureParentDir(filepath) {
  await fs.mkdir(path.dirname(filepath), { recursive: true });
}

function parseLinksFromPre(preHtml) {
  const $ = load(`<div id="wrap">${preHtml}</div>`);

  const links = [];
  $('#wrap a').each((_, el) => {
    const href = ($(el).attr('href') ?? '').trim();
    const label = ($(el).text() ?? '').trim();

    // Skip parent directory / empty
    if (!href || href === '../' || label.toLowerCase().includes('parent directory')) return;

    const isDir = href.endsWith('/');

    // Some listings contain "annotation_hashes.txt" etc. Keep them too unless you want only dirs
    const bacteriaName = label.replace(/\/$/, '').trim();

    // Make a clean absolute source URL pointing to NCBI, not the local file
    const sourceUrl = new URL(href, NCBI_BACTERIA_BASE_URL).toString();

    links.push({
      bacteria_name: bacteriaName,
      source_url: sourceUrl,
      is_dir: isDir,
    });
  });

  return links;
}

async function saveBacteriaToJsonl(preHtml) {
  const links = parseLinksFromPre(preHtml);

  const progressBar = new cliProgress.SingleBar({ format: 'processing [{bar}] {value}/{total} links', hideCursor: true }, cliProgress.Presets.shades_classic);

  progressBar.start(links.length, 0);

  const jsonlLines = [];
  for (const record of links) {
    jsonlLines.push(JSON.stringify(record) + '\n');
    progressBar.increment();
  }

  progressBar.stop();

  await ensureParentDir(OUTPUT_JSONL_PATH);
  await fs.writeFile(OUTPUT_JSONL_PATH, jsonlLines.join(''), 'utf8');

  console.log(`Saved ${links.length} records to ${OUTPUT_JSONL_PATH}`);
}

async function run() {
  const fileContent = await fs.readFile(new URL(LISTING_HTML_FILE), 'utf8');

  const preStart = fileContent.indexOf('<pre>');
  const preEnd = fileContent.indexOf('</pre>');

  if (preStart === -1 || preEnd === -1 || preEnd <= preStart) {
    throw new Error('Could not find <pre>...</pre> block in the downloaded listing HTML.');
  }

  const preHtml = fileContent.substring(preStart + 5, preEnd);
  await saveBacteriaToJsonl(preHtml);

  console.log('Done!');
}

run().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
