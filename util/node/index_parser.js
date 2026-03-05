import * as cheerio from 'cheerio';

export function parseDirectoryLinks({ html, pageUrl } = {}) {
  const $ = cheerio.load(html);
  const links = [];

  $('pre a').each((_, anchor) => {
    const href = ($(anchor).attr('href') ?? '').trim();
    const label = $(anchor).text().trim();

    if (!href || !label || label.toLowerCase() === 'parent directory') {
      return;
    }

    const absoluteUrl = new URL(href, pageUrl).toString();
    links.push({
      href,
      label,
      url: absoluteUrl,
      isDirectory: href.endsWith('/'),
    });
  });

  return links;
}

export function splitVersionEntries({ links } = {}) {
  const normalizedLinks = links ?? [];

  const versions = normalizedLinks.map(({ url, label }) => ({
    version_url: url,
    version_label: label,
  }));

  return versions;
}
