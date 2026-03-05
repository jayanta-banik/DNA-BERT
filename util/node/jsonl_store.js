import { buildRowKey } from '#util/path_utils';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import readline from 'node:readline';

export function createSummaryRow({
  bacteriaName,
  sourceUrl,
  latestAssemblyVersionsAvailable,
  discoveredVersionCount,
  downloadedFileCount,
  downloadCompleted,
  versions,
  status,
  errorMessage,
} = {}) {
  const normalizedErrorMessage = status === 'failed' && (!errorMessage || !String(errorMessage).trim()) ? 'unknown_error' : errorMessage;

  const summaryRow = {
    bacteria_name: bacteriaName,
    source_url: sourceUrl,
    latest_assembly_versions_available: Boolean(latestAssemblyVersionsAvailable),
    discovered_version_count: Number(discoveredVersionCount ?? 0),
    downloaded_file_count: Number(downloadedFileCount ?? 0),
    download_completed: Boolean(downloadCompleted),
    versions: versions ?? [],
    status,
  };

  if (normalizedErrorMessage) {
    summaryRow.error_message = String(normalizedErrorMessage);
  }

  return summaryRow;
}

export function validateSummaryRow({ summaryRow } = {}) {
  if (!summaryRow || typeof summaryRow !== 'object') {
    throw new Error('Summary row must be an object');
  }

  const requiredStringFields = ['bacteria_name', 'source_url', 'status'];
  for (const field of requiredStringFields) {
    if (typeof summaryRow[field] !== 'string' || !summaryRow[field].trim()) {
      throw new Error(`Invalid summary field: ${field}`);
    }
  }

  if (!['success', 'failed', 'skipped'].includes(summaryRow.status)) {
    throw new Error(`Invalid summary status: ${summaryRow.status}`);
  }

  if (typeof summaryRow.latest_assembly_versions_available !== 'boolean') {
    throw new Error('latest_assembly_versions_available must be boolean');
  }

  if (!Number.isInteger(summaryRow.discovered_version_count) || summaryRow.discovered_version_count < 0) {
    throw new Error('discovered_version_count must be a non-negative integer');
  }

  if (!Number.isInteger(summaryRow.downloaded_file_count) || summaryRow.downloaded_file_count < 0) {
    throw new Error('downloaded_file_count must be a non-negative integer');
  }

  if (typeof summaryRow.download_completed !== 'boolean') {
    throw new Error('download_completed must be boolean');
  }

  if (!Array.isArray(summaryRow.versions)) {
    throw new Error('versions must be an array');
  }

  for (const version of summaryRow.versions) {
    if (!version || typeof version !== 'object') {
      throw new Error('Each version must be an object');
    }

    if (typeof version.version_url !== 'string' || !version.version_url.trim()) {
      throw new Error('version_url must be a non-empty string');
    }

    if (typeof version.version_label !== 'string' || !version.version_label.trim()) {
      throw new Error('version_label must be a non-empty string');
    }
  }

  if (summaryRow.status === 'failed' && (!summaryRow.error_message || !summaryRow.error_message.trim())) {
    throw new Error('error_message is required when status is failed');
  }
}

export async function loadPriorSummaryMap({ outFilePath } = {}) {
  const summaryMap = new Map();

  try {
    await fsp.access(outFilePath);
  } catch {
    return summaryMap;
  }

  const stream = fs.createReadStream(outFilePath, { encoding: 'utf8' });
  const lineReader = readline.createInterface({ input: stream, crlfDelay: Infinity });

  for await (const line of lineReader) {
    const trimmedLine = line.trim();
    if (!trimmedLine) {
      continue;
    }

    try {
      const summaryRow = JSON.parse(trimmedLine);
      const rowKey = buildRowKey({
        bacteriaName: summaryRow.bacteria_name,
        sourceUrl: summaryRow.source_url,
      });
      summaryMap.set(rowKey, summaryRow);
    } catch {
      // Ignore malformed prior lines; current run will regenerate clean output.
    }
  }

  return summaryMap;
}

export async function appendSummaryRow({ outFilePath, summaryRow } = {}) {
  validateSummaryRow({ summaryRow });
  const jsonLine = `${JSON.stringify(summaryRow)}\n`;
  await fsp.appendFile(outFilePath, jsonLine, 'utf8');
}

export async function writeSummaryRows({ outFilePath, summaryRows } = {}) {
  const lines = [];
  for (const summaryRow of summaryRows) {
    validateSummaryRow({ summaryRow });
    lines.push(`${JSON.stringify(summaryRow)}\n`);
  }

  await fsp.writeFile(outFilePath, lines.join(''), 'utf8');
}

export async function validateSummaryRowsAgainstSchema({ schemaPath, summaryRows } = {}) {
  const schemaText = await fsp.readFile(schemaPath, 'utf8');
  const schema = JSON.parse(schemaText);

  const requiredFields = schema.required ?? [];
  const statusEnum = schema.properties?.status?.enum ?? ['success', 'failed', 'skipped'];

  for (const summaryRow of summaryRows) {
    validateSummaryRow({ summaryRow });

    for (const field of requiredFields) {
      if (!(field in summaryRow)) {
        throw new Error(`Schema validation failed: missing required field '${field}'`);
      }
    }

    if (!statusEnum.includes(summaryRow.status)) {
      throw new Error(`Schema validation failed: invalid status '${summaryRow.status}'`);
    }
  }
}
