import * as cheerio from 'cheerio';
import got from 'got';

const REQUEST_TIMEOUT_MS = 30000;

export function fetchWithRetry({ sourceUrl, options = {}, retries = 5, retryDelayMs = 1000 }) {
  return got(sourceUrl, {
    ...options,
    retry: {
      limit: retries,
      methods: ['GET'],
      statusCodes: [408, 429, 500, 502, 503, 504],
      errorCodes: ['ETIMEDOUT', 'ECONNRESET', 'EAI_AGAIN'],
      calculateDelay: ({ attemptCount, retryOptions, error }) => {
        if (attemptCount > retryOptions.limit) return 0;
        return retryDelayMs * attemptCount; // exponential-ish backoff
      },
    },
    throwHttpErrors: true,
    timeout: { request: REQUEST_TIMEOUT_MS },
  });
}

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
