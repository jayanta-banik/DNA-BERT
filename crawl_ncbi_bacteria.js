import * as cheerio from 'cheerio';
import fs from 'fs';
import got from 'got';
import pLimit from 'p-limit';
import path from 'path';

const baseURL = 'https://ftp.ncbi.nlm.nih.gov/genomes/genbank/bacteria/';
const htmlFile = 'Index of _genomes_genbank_bacteria.html'; // your local file
const outFile = 'ncbi_bacteria_links.jsonl'; // output (one JSON per line)

const CONCURRENCY = 8; // be polite; you can tune
const limit = pLimit(CONCURRENCY);

function extractBaseLinksFromLocalHtml(localHtml, base) {
  const $ = cheerio.load(localHtml);
  const links = [];
  $('a[href]').each((_, el) => {
    const href = $(el).attr('href');
    if (href && href.startsWith(base)) links.push(href);
  });
  return Array.from(new Set(links));
}

function cleanName(text, href) {
  const name = text && text.trim() ? text.trim() : href;
  return name;
}

function isDir(name, href) {
  return name?.endsWith('/') || href?.endsWith('/');
}

function isParentDirectory(name) {
  return (name || '').trim().toLowerCase() === 'parent directory';
}

async function fetchPreLinks(url) {
  const res = await got(url, {
    timeout: { request: 60_000 },
    retry: { limit: 3 },
    headers: {
      // avoid being mistaken for a botnet with empty UA
      'user-agent': 'ncbi-dir-crawler/1.0 (contact: you@example.com)',
    },
  });

  const $ = cheerio.load(res.body);
  const pre = $('pre').first();
  if (!pre.length) {
    throw new Error(`No <pre> tag found at ${url}`);
  }

  const rows = [];
  pre.find('a[href]').each((_, el) => {
    const href = $(el).attr('href');
    const text = $(el).text().trim();

    if (!href) return;

    const absUrl = new URL(href, url.endsWith('/') ? url : url + '/').toString();
    const name = cleanName(text, href);

    if (isParentDirectory(name)) return;

    rows.push({
      source_url: url,
      text,
      href,
      abs_url: absUrl,
      name,
      is_dir: isDir(name, href),
    });
  });

  return rows;
}

async function main() {
  const localHtml = fs.readFileSync(htmlFile, 'utf8');
  const links = extractBaseLinksFromLocalHtml(localHtml, baseURL);

  console.log(`Found ${links.length} base links in ${htmlFile}`);

  // reset output
  fs.writeFileSync(outFile, '', 'utf8');

  let ok = 0;
  let fail = 0;

  // crawl with concurrency + stream to JSONL
  const tasks = links.map((url, idx) =>
    limit(async () => {
      try {
        const rows = await fetchPreLinks(url);

        // write each row as a JSON line
        const lines = rows.map((r) => JSON.stringify(r)).join('\n') + '\n';
        fs.appendFileSync(outFile, lines, 'utf8');

        ok += 1;
        if (idx % 50 === 0) console.log(`Progress: ${idx}/${links.length} ... ok=${ok} fail=${fail} ... completed: ${((idx / links.length) * 100).toFixed(2)}%`);
      } catch (e) {
        fail += 1;
        console.error(`Error fetching ${url}: ${e.message}`);
      }
    }),
  );

  await Promise.all(tasks);

  console.log(`Done. ok=${ok} fail=${fail}`);
  console.log(`Saved: ${path.resolve(outFile)}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
