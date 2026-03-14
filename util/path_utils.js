import fs from 'node:fs/promises';
import path from 'node:path';

export function sanitizeBacteriaName({ bacteriaName } = {}) {
  const trimmedName = (bacteriaName ?? '').trim();
  const safeName = trimmedName
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '');

  return safeName || 'unnamed_bacteria';
}

export function buildLatestAssemblyUrl({ sourceUrl } = {}) {
  const normalizedSourceUrl = sourceUrl.endsWith('/') ? sourceUrl : `${sourceUrl}/`;
  return new URL('latest_assembly_versions/', normalizedSourceUrl).toString();
}

export function buildRowKey({ bacteriaName, sourceUrl } = {}) {
  return `${bacteriaName}||${sourceUrl}`;
}

export function mapRemotePathToLocal({ latestAssemblyRootUrl, fileUrl, bacteriaOutputDir } = {}) {
  const rootPath = new URL(latestAssemblyRootUrl).pathname;
  const filePath = new URL(fileUrl).pathname;
  let relativePath = path.posix.relative(rootPath, filePath);

  // Guard against malformed links escaping the latest_assembly_versions subtree.
  if (!relativePath || relativePath.startsWith('..')) {
    relativePath = path.posix.basename(filePath);
  }

  const localPath = path.join(bacteriaOutputDir, ...relativePath.split('/'));
  return localPath;
}

async function countFilesRecursive({ dirPath } = {}) {
  let fileCount = 0;
  const entries = await fs.readdir(dirPath, { withFileTypes: true });

  for (const entry of entries) {
    const entryPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      fileCount += await countFilesRecursive({ dirPath: entryPath });
    } else if (entry.isFile()) {
      fileCount += 1;
    }
  }

  return fileCount;
}

export async function hasConsistentOutput({ bacteriaOutputDir, expectedDownloadedFileCount } = {}) {
  try {
    const stat = await fs.stat(bacteriaOutputDir);
    if (!stat.isDirectory()) {
      return false;
    }

    const actualFileCount = await countFilesRecursive({ dirPath: bacteriaOutputDir });
    return actualFileCount >= Number(expectedDownloadedFileCount ?? 0);
  } catch {
    return false;
  }
}

export async function clearRowOutput({ bacteriaOutputDir } = {}) {
  await fs.rm(bacteriaOutputDir, { recursive: true, force: true });
}

export async function ensureDirectory({ dirPath } = {}) {
  await fs.mkdir(dirPath, { recursive: true });
}
