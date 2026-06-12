#!/usr/bin/env node

import cliProgress from 'cli-progress';
import { parse as parseCsv } from 'csv-parse/sync';
import { stringify as stringifyCsv } from 'csv-stringify/sync';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import OpenAI from 'openai';
import { z } from 'zod';

import { fileExists } from '../../util/path_utils.js';
import { sleep } from '../../util/timers.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const ARTIFACT_DIR = path.join(REPO_ROOT, 'results', 'protein_tokenization', 'artifacts');

const DEFAULT_SOURCE_PATH = path.join(ARTIFACT_DIR, 'semantic_annotation_matches.csv');
const DEFAULT_CHECKPOINT_PATH = path.join(ARTIFACT_DIR, 'semantic_annotation_matches_checkpoint.csv');
const DEFAULT_OUTPUT_PATH = path.join(ARTIFACT_DIR, 'semantic_annotation_amr_labels.csv');

const DEFAULT_MODEL = 'gpt-5.4';
const DEFAULT_BATCH_SIZE = 15;
const DEFAULT_REQUEST_BATCH_SIZE = 20;
const DEFAULT_STAGGER_MS = 100;
const DEFAULT_MAX_RETRIES = 4;
const DEFAULT_RETRY_DELAY_MS = 1000;

const STATUS_PENDING = 'pending';
const STATUS_COMPLETED = 'completed';
const STATUS_FAILED = 'failed';

const CATEGORIES = ['antibiotic_resistance', 'non_amr_antibiotic_biosynthesis', 'non_amr_transport', 'non_amr_metal_resistance', 'non_amr_virulence', 'ambiguous', 'unknown'];
const RESULT_FIELDS = ['annotation', 'is_amr', 'category', 'confidence', 'evidence_terms', 'reason'];

const CHECKPOINT_EXTRA_COLUMNS = ['status', ...RESULT_FIELDS.slice(1), 'error_message', 'retry_count', 'completed_at', 'updated_at'];

const OUTPUT_COLUMNS = [...RESULT_FIELDS, 'row_idx'];

const DEVELOPER_PROMPT = [
  'You are classifying biological annotations for antimicrobial resistance (AMR).',
  'You will receive a JSON array of input rows with row_idx and annotation.',
  'Return a JSON object with a results array containing exactly one output object per input row.',
  'Each output object must preserve the same row_idx and should echo the annotation from the input.',
  'Only include row_idx, annotation, is_amr, category, confidence, evidence_terms, and reason in each result object.',
  'Do not omit rows, duplicate rows, merge rows, or invent rows.',
  'confidence must be a number between 0 and 1.',
  'evidence_terms must be a non-empty array of concise strings copied from or directly grounded in the annotation.',
  'reason must be a non-empty short explanation for the classification.',
  '',
  'AMR includes:',
  '- antibiotic resistance proteins',
  '- efflux pumps specific to antibiotics',
  '- beta-lactamases',
  '- target modification/protection',
  '- antimicrobial peptide resistance',
  '',
  'NOT AMR:',
  '- antibiotic biosynthesis',
  '- metabolism',
  '- virulence',
  '- metal resistance',
  '- generic transport unless clearly resistance-related',
].join('\n');

const amrLabelResultSchema = z.object({
  row_idx: z.number().int().nonnegative(),
  annotation: z.string().trim().min(1),
  is_amr: z.boolean(),
  category: z.enum(CATEGORIES),
  confidence: z.number().min(0).max(1),
  evidence_terms: z.array(z.string().trim().min(1)).min(1),
  reason: z.string().trim().min(1),
});

const amrLabelSchema = z.object({ results: z.array(amrLabelResultSchema) });

function createAmrLabelResponseSchema(expectedLength) {
  return {
    type: 'object',
    additionalProperties: false,
    properties: {
      results: {
        type: 'array',
        minItems: expectedLength,
        maxItems: expectedLength,
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            row_idx: { type: 'integer', minimum: 0 },
            annotation: { type: 'string' },
            is_amr: { type: 'boolean' },
            category: { type: 'string', enum: CATEGORIES },
            confidence: { type: 'number', minimum: 0, maximum: 1 },
            evidence_terms: {
              type: 'array',
              minItems: 1,
              items: { type: 'string' },
            },
            reason: { type: 'string', minLength: 1 },
          },
          required: ['row_idx', 'annotation', 'is_amr', 'category', 'confidence', 'evidence_terms', 'reason'],
        },
      },
    },
    required: ['results'],
  };
}

function printHelp() {
  console.log(
    [
      'Usage: yarn annotate:amr -- [options]',
      '',
      'Options:',
      '  --source PATH            Source semantic matches CSV',
      '  --checkpoint PATH        Checkpoint CSV path',
      '  --output PATH            Final AMR labels CSV path',
      '  --model NAME             Model name',
      `  --batch-size N           Rows per model request batch (default: ${DEFAULT_BATCH_SIZE})`,
      `  --request-batch-size N   Concurrent request batches per wave (default: ${DEFAULT_REQUEST_BATCH_SIZE})`,
      `  --stagger-ms N           Delay between batch requests (default: ${DEFAULT_STAGGER_MS})`,
      `  --max-retries N          Retry count per row for transient failures (default: ${DEFAULT_MAX_RETRIES})`,
      `  --retry-delay-ms N       Base backoff delay in ms (default: ${DEFAULT_RETRY_DELAY_MS})`,
      '  --start-row N            Start processing at row_idx >= N',
      '  --limit N                Limit pending rows for this run',
      '  --help                   Show this message',
      '',
      'Required environment:',
      '  OPENAI_API_KEY',
    ].join('\n'),
  );
}

function parseArgs(argv) {
  const options = {
    sourcePath: DEFAULT_SOURCE_PATH,
    checkpointPath: DEFAULT_CHECKPOINT_PATH,
    outputPath: DEFAULT_OUTPUT_PATH,
    model: DEFAULT_MODEL,
    batchSize: DEFAULT_BATCH_SIZE,
    requestBatchSize: DEFAULT_REQUEST_BATCH_SIZE,
    staggerMs: DEFAULT_STAGGER_MS,
    maxRetries: DEFAULT_MAX_RETRIES,
    retryDelayMs: DEFAULT_RETRY_DELAY_MS,
    startRow: 0,
    limit: null,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];

    if (arg === '--help') {
      options.help = true;
      continue;
    }

    if (arg === '--source') {
      options.sourcePath = next;
      index += 1;
      continue;
    }

    if (arg === '--checkpoint') {
      options.checkpointPath = next;
      index += 1;
      continue;
    }

    if (arg === '--output') {
      options.outputPath = next;
      index += 1;
      continue;
    }

    if (arg === '--model') {
      options.model = next;
      index += 1;
      continue;
    }

    if (arg === '--batch-size') {
      options.batchSize = parseIntegerOption(next, arg);
      index += 1;
      continue;
    }

    if (arg === '--request-batch-size') {
      options.requestBatchSize = parseIntegerOption(next, arg);
      index += 1;
      continue;
    }

    if (arg === '--stagger-ms') {
      options.staggerMs = parseIntegerOption(next, arg);
      index += 1;
      continue;
    }

    if (arg === '--max-retries') {
      options.maxRetries = parseIntegerOption(next, arg);
      index += 1;
      continue;
    }

    if (arg === '--retry-delay-ms') {
      options.retryDelayMs = parseIntegerOption(next, arg);
      index += 1;
      continue;
    }

    if (arg === '--start-row') {
      options.startRow = parseIntegerOption(next, arg);
      index += 1;
      continue;
    }

    if (arg === '--limit') {
      options.limit = parseIntegerOption(next, arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (options.batchSize <= 0) throw new Error('--batch-size must be greater than 0');
  if (options.requestBatchSize <= 0) throw new Error('--request-batch-size must be greater than 0');
  if (options.staggerMs < 0) throw new Error('--stagger-ms must be 0 or greater');
  if (options.maxRetries < 0) throw new Error('--max-retries must be 0 or greater');
  if (options.retryDelayMs < 0) throw new Error('--retry-delay-ms must be 0 or greater');
  if (options.startRow < 0) throw new Error('--start-row must be 0 or greater');
  if (options.limit !== null && options.limit < 0) throw new Error('--limit must be 0 or greater');

  return options;
}

function parseIntegerOption(value, flagName) {
  const parsed = Number.parseInt(value ?? '', 10);
  if (!Number.isInteger(parsed)) {
    throw new Error(`${flagName} expects an integer value`);
  }
  return parsed;
}

function chunkRows(rows, chunkSize) {
  const chunks = [];

  for (let index = 0; index < rows.length; index += chunkSize) {
    chunks.push(rows.slice(index, index + chunkSize));
  }

  return chunks;
}

async function readCsv(filePath, { ignoreMissing = false } = {}) {
  const exists = await fileExists(filePath);
  if (!exists) {
    if (ignoreMissing) return [];
    throw new Error(`Missing CSV file: ${filePath}`);
  }

  const text = await fs.readFile(filePath, 'utf8');
  if (!text.trim()) return [];

  return parseCsv(text, {
    columns: true,
    skip_empty_lines: true,
    trim: false,
  });
}

async function writeCsvAtomic(filePath, rows, columns) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });

  const records = rows.map((row) => {
    const record = {};
    for (const column of columns) {
      record[column] = serializeCsvValue(row[column]);
    }
    return record;
  });

  const csv = stringifyCsv(records, { header: true, columns });
  const tempPath = `${filePath}.tmp`;
  await fs.writeFile(tempPath, csv, 'utf8');
  await fs.rename(tempPath, filePath);
}

function serializeCsvValue(value) {
  if (value === null || value === undefined) return '';
  if (Array.isArray(value)) return JSON.stringify(value);
  return value;
}

function ensureRequiredColumns(rows, requiredColumns, filePath) {
  if (rows.length === 0) {
    throw new Error(`CSV file is empty: ${filePath}`);
  }

  const rowColumns = new Set(Object.keys(rows[0]));
  const missing = requiredColumns.filter((column) => !rowColumns.has(column));
  if (missing.length > 0) {
    throw new Error(`CSV file ${filePath} is missing columns: ${missing.join(', ')}`);
  }
}

function normalizeSourceRows(rows, filePath) {
  ensureRequiredColumns(rows, ['annotation'], filePath);

  return rows.map((row, index) => ({
    row_idx: index,
    annotation: String(row.annotation ?? '').trim(),
    score: parseOptionalNumber(row.score),
    semantic_rank: parseOptionalInteger(row.semantic_rank),
    status: STATUS_PENDING,
    is_amr: null,
    category: '',
    confidence: null,
    evidence_terms: [],
    reason: '',
    error_message: '',
    retry_count: 0,
    completed_at: '',
    updated_at: '',
  }));
}

function normalizeCheckpointRows(rows, filePath) {
  ensureRequiredColumns(rows, ['row_idx', 'annotation'], filePath);

  return rows.map((row) => ({
    row_idx: parseIntegerLike(row.row_idx, 'row_idx', filePath),
    annotation: String(row.annotation ?? '').trim(),
    score: parseOptionalNumber(row.score),
    semantic_rank: parseOptionalInteger(row.semantic_rank),
    status: normalizeStatus(row.status),
    is_amr: parseOptionalBoolean(row.is_amr),
    category: normalizeCategory(row.category),
    confidence: parseOptionalConfidence(row.confidence),
    evidence_terms: parseEvidenceTerms(row.evidence_terms),
    reason: String(row.reason ?? ''),
    error_message: String(row.error_message ?? ''),
    retry_count: parseOptionalInteger(row.retry_count) ?? 0,
    completed_at: String(row.completed_at ?? ''),
    updated_at: String(row.updated_at ?? ''),
  }));
}

function normalizeLegacyOutputRows(rows, filePath) {
  if (rows.length === 0) return [];
  ensureRequiredColumns(rows, OUTPUT_COLUMNS, filePath);

  return rows.map((row) => ({
    row_idx: parseIntegerLike(row.row_idx, 'row_idx', filePath),
    annotation: String(row.annotation ?? '').trim(),
    is_amr: parseBooleanLike(row.is_amr, 'is_amr', filePath),
    category: normalizeCategory(row.category, filePath),
    confidence: parseConfidenceLike(row.confidence, filePath),
    evidence_terms: parseEvidenceTerms(row.evidence_terms),
    reason: String(row.reason ?? ''),
  }));
}

function normalizeStatus(value) {
  if (value === STATUS_COMPLETED || value === STATUS_FAILED || value === STATUS_PENDING) {
    return value;
  }
  return STATUS_PENDING;
}

function normalizeCategory(value, filePath = 'checkpoint') {
  const normalized = String(value ?? '').trim();
  if (!normalized) return '';
  if (!CATEGORIES.includes(normalized)) {
    throw new Error(`Invalid category '${normalized}' in ${filePath}`);
  }
  return normalized;
}

function parseOptionalInteger(value) {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number.parseInt(String(value), 10);
  return Number.isInteger(parsed) ? parsed : null;
}

function parseIntegerLike(value, fieldName, filePath) {
  const parsed = parseOptionalInteger(value);
  if (parsed === null) {
    throw new Error(`Invalid ${fieldName} in ${filePath}`);
  }
  return parsed;
}

function parseOptionalNumber(value) {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number.parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : null;
}

function parseOptionalConfidence(value) {
  const parsed = parseOptionalNumber(value);
  if (parsed === null) return null;
  if (parsed < 0 || parsed > 1) return null;
  return parsed;
}

function parseConfidenceLike(value, filePath) {
  const parsed = parseOptionalConfidence(value);
  if (parsed === null) {
    throw new Error(`Invalid confidence value in ${filePath}`);
  }
  return parsed;
}

function parseOptionalBoolean(value) {
  if (value === '' || value === null || value === undefined) return null;
  const normalized = String(value).trim().toLowerCase();
  if (normalized === 'true') return true;
  if (normalized === 'false') return false;
  return null;
}

function parseBooleanLike(value, fieldName, filePath) {
  const parsed = parseOptionalBoolean(value);
  if (parsed === null) {
    throw new Error(`Invalid ${fieldName} in ${filePath}`);
  }
  return parsed;
}

function parseEvidenceTerms(value) {
  if (Array.isArray(value)) return value.map((item) => String(item));
  if (value === '' || value === null || value === undefined) return [];

  const text = String(value).trim();
  if (!text) return [];

  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      return parsed.map((item) => String(item));
    }
  } catch {
    // Fall through to Python-list parsing.
  }

  const quotedMatches = [...text.matchAll(/'([^']*)'|"([^"]*)"/g)];
  if (quotedMatches.length > 0) {
    return quotedMatches.map((match) => String(match[1] ?? match[2] ?? ''));
  }

  if (text.startsWith('[') && text.endsWith(']')) {
    return text
      .slice(1, -1)
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => item.replace(/^['"]|['"]$/g, ''));
  }

  return [text];
}

function checkpointColumnsForRows() {
  return ['row_idx', 'annotation', 'score', 'semantic_rank', ...CHECKPOINT_EXTRA_COLUMNS];
}

function buildOutputRows(checkpointRows) {
  return checkpointRows
    .filter((row) => row.status === STATUS_COMPLETED)
    .sort((left, right) => left.row_idx - right.row_idx)
    .map((row) => ({
      annotation: row.annotation,
      is_amr: row.is_amr,
      category: row.category,
      confidence: row.confidence,
      evidence_terms: row.evidence_terms,
      reason: row.reason,
      row_idx: row.row_idx,
    }));
}

async function persistState(checkpointRows, checkpointPath, outputPath) {
  await writeCsvAtomic(checkpointPath, checkpointRows, checkpointColumnsForRows());
  await writeCsvAtomic(outputPath, buildOutputRows(checkpointRows), OUTPUT_COLUMNS);
}

async function initializeCheckpoint(options) {
  const sourceRows = normalizeSourceRows(await readCsv(options.sourcePath), options.sourcePath);

  if (await fileExists(options.checkpointPath)) {
    const checkpointRows = normalizeCheckpointRows(await readCsv(options.checkpointPath), options.checkpointPath);
    await persistState(checkpointRows, options.checkpointPath, options.outputPath);
    return { checkpointRows, bootstrappedLegacyCount: 0, createdCheckpoint: false };
  }

  const checkpointRows = sourceRows.map((row) => ({ ...row }));
  let bootstrappedLegacyCount = 0;

  if (await fileExists(options.outputPath)) {
    const legacyRows = normalizeLegacyOutputRows(await readCsv(options.outputPath, { ignoreMissing: true }), options.outputPath);
    const checkpointByRow = new Map(checkpointRows.map((row) => [row.row_idx, row]));

    for (const legacyRow of legacyRows) {
      const checkpointRow = checkpointByRow.get(legacyRow.row_idx);
      if (!checkpointRow) continue;

      checkpointRow.status = STATUS_COMPLETED;
      checkpointRow.annotation = legacyRow.annotation || checkpointRow.annotation;
      checkpointRow.is_amr = legacyRow.is_amr;
      checkpointRow.category = legacyRow.category;
      checkpointRow.confidence = legacyRow.confidence;
      checkpointRow.evidence_terms = legacyRow.evidence_terms;
      checkpointRow.reason = legacyRow.reason;
      checkpointRow.error_message = '';
      checkpointRow.completed_at = checkpointRow.completed_at || new Date().toISOString();
      checkpointRow.updated_at = new Date().toISOString();
      bootstrappedLegacyCount += 1;
    }
  }

  await persistState(checkpointRows, options.checkpointPath, options.outputPath);
  return { checkpointRows, bootstrappedLegacyCount, createdCheckpoint: true };
}

function createProgressBar(totalPending, checkpointRows) {
  const progressBar = new cliProgress.SingleBar(
    {
      format: 'amr [{bar}] {value}/{total} run | completed {completed}/{datasetTotal} | failed {failed} | retries {retries} | batch {batch} | eta {eta_formatted}',
      hideCursor: true,
      clearOnComplete: true,
      etaBuffer: Math.max(10, Math.min(totalPending, 50)),
    },
    cliProgress.Presets.shades_classic,
  );

  progressBar.start(totalPending, 0, {
    completed: checkpointRows.filter((row) => row.status === STATUS_COMPLETED).length,
    datasetTotal: checkpointRows.length,
    failed: checkpointRows.filter((row) => row.status === STATUS_FAILED).length,
    retries: 0,
    batch: '0/0',
  });

  return progressBar;
}

function createPersistQueue(checkpointRows, checkpointPath, outputPath) {
  let chain = Promise.resolve();

  return {
    enqueue() {
      chain = chain.then(() => persistState(checkpointRows, checkpointPath, outputPath));
      return chain;
    },
    flush() {
      return chain;
    },
  };
}

function isRetryableError(error) {
  const status = error?.status ?? error?.statusCode ?? error?.response?.status ?? error?.response?.statusCode;
  if ([408, 409, 429, 500, 502, 503, 504].includes(status)) return true;

  const code = String(error?.code ?? '').toUpperCase();
  return ['ECONNRESET', 'ETIMEDOUT', 'EAI_AGAIN', 'ENOTFOUND', 'ECONNREFUSED'].includes(code);
}

function extractMessageText(message) {
  if (!message) return '';
  if (typeof message.content === 'string') return message.content;
  if (Array.isArray(message.content)) {
    return message.content
      .map((part) => {
        if (typeof part === 'string') return part;
        if (part?.type === 'text' || part?.type === 'output_text') return part.text ?? '';
        return '';
      })
      .join('')
      .trim();
  }
  return '';
}

function formatZodError(error) {
  return error.issues
    .map((issue) => {
      const location = issue.path.length > 0 ? issue.path.join('.') : 'root';
      return `${location}: ${issue.message}`;
    })
    .join('; ');
}

function validateModelLabels(payload, rows) {
  const parsed = amrLabelSchema.safeParse(payload);
  if (!parsed.success) {
    throw new Error(`Model output failed Zod validation: ${formatZodError(parsed.error)}`);
  }

  if (parsed.data.results.length !== rows.length) {
    throw new Error(`Model returned ${parsed.data.results.length} labels for ${rows.length} rows`);
  }

  const expectedRows = new Map(rows.map((row) => [row.row_idx, row]));
  const labelsByRow = new Map();

  for (const label of parsed.data.results) {
    if (!expectedRows.has(label.row_idx)) {
      throw new Error(`Model returned unexpected row_idx=${label.row_idx}`);
    }

    if (labelsByRow.has(label.row_idx)) {
      throw new Error(`Model returned duplicate row_idx=${label.row_idx}`);
    }

    labelsByRow.set(label.row_idx, label);
  }

  for (const row of rows) {
    if (!labelsByRow.has(row.row_idx)) {
      throw new Error(`Model omitted row_idx=${row.row_idx}`);
    }
  }

  return rows.map((row) => labelsByRow.get(row.row_idx));
}

async function requestAmrLabels(client, rows, options) {
  const batchInput = rows.map((row) => ({
    row_idx: row.row_idx,
    annotation: row.annotation,
  }));

  const completion = await client.chat.completions.create({
    model: options.model,
    messages: [
      { role: 'developer', content: DEVELOPER_PROMPT },
      {
        role: 'user',
        content: [
          'Classify every annotation in this batch.',
          'The results field must be an array with exactly one result per input row.',
          'Each result object must include row_idx, annotation, is_amr, category, confidence, evidence_terms, and reason.',
          'Echo annotation from the input, but row_idx is the source of truth for mapping.',
          JSON.stringify(batchInput, null, 2),
        ].join('\n\n'),
      },
    ],
    response_format: {
      type: 'json_schema',
      json_schema: {
        name: 'amr_annotation_label_batch',
        strict: true,
        schema: createAmrLabelResponseSchema(rows.length),
      },
    },
  });

  const message = completion.choices?.[0]?.message;
  if (message?.refusal) {
    throw new Error(`Model refused the request: ${message.refusal}`);
  }

  const text = extractMessageText(message);
  if (!text) {
    throw new Error('Model returned an empty response');
  }

  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error(`Model returned invalid JSON: ${text}`);
  }

  return validateModelLabels(parsed, rows);
}

function buildProgressPayload(state) {
  return {
    completed: state.completed,
    datasetTotal: state.datasetTotal,
    failed: state.failed,
    retries: state.retries,
    batch: `${state.batchIndex}/${state.totalBatches}`,
  };
}

async function classifyBatchWithRetry(client, rows, options, state, progressBar) {
  let lastError;

  for (let attempt = 0; attempt <= options.maxRetries; attempt += 1) {
    try {
      return {
        labels: await requestAmrLabels(client, rows, options),
        retryCount: attempt,
      };
    } catch (error) {
      lastError = error;
      if (!isRetryableError(error) || attempt === options.maxRetries) {
        if (lastError && typeof lastError === 'object') {
          lastError.retryCount = attempt;
        }
        throw lastError;
      }

      state.retries += 1;
      progressBar.update(state.processed, buildProgressPayload(state));
      await sleep(options.retryDelayMs * (attempt + 1));
    }
  }

  throw lastError;
}

function createBatchFailureMessage(rows, error) {
  const status = error?.status ?? error?.statusCode ?? error?.response?.status ?? error?.response?.statusCode;
  const code = error?.code ? ` code=${error.code}` : '';
  const prefix = status ? `status=${status}` : 'non-retryable';
  const rowIdxs = rows.map((row) => row.row_idx).join(',');
  return `${prefix}${code} ${error?.message ?? String(error)} for batch row_idxs=${rowIdxs}`;
}

async function processBatch(batchRows, options, runtime) {
  try {
    const result = await classifyBatchWithRetry(runtime.client, batchRows, options, runtime.state, runtime.progressBar);

    for (const [index, row] of batchRows.entries()) {
      const label = result.labels[index];
      row.status = STATUS_COMPLETED;
      row.is_amr = label.is_amr;
      row.category = label.category;
      row.confidence = label.confidence;
      row.evidence_terms = label.evidence_terms;
      row.reason = label.reason;
      row.error_message = '';
      row.retry_count = result.retryCount;
      row.completed_at = row.completed_at || new Date().toISOString();
      row.updated_at = new Date().toISOString();

      await runtime.persistQueue.enqueue();

      runtime.state.processed += 1;
      runtime.state.completed += 1;
      runtime.progressBar.increment(1, buildProgressPayload(runtime.state));
    }

    return;
  } catch (error) {
    const errorMessage = createBatchFailureMessage(batchRows, error);

    for (const row of batchRows) {
      row.status = STATUS_FAILED;
      row.error_message = errorMessage;
      row.retry_count = parseOptionalInteger(error?.retryCount) ?? 0;
      row.updated_at = new Date().toISOString();

      await runtime.persistQueue.enqueue();

      runtime.state.processed += 1;
      runtime.state.failed += 1;
      runtime.progressBar.increment(1, buildProgressPayload(runtime.state));
    }

    throw new Error(errorMessage);
  }
}

async function processBatchWave(batchGroups, options, runtime) {
  const batchPromises = batchGroups.map((batchRows, waveIndex) => {
    runtime.state.batchIndex += 1;
    runtime.progressBar.update(runtime.state.processed, buildProgressPayload(runtime.state));

    return (async () => {
      if (waveIndex > 0 && options.staggerMs > 0) {
        await sleep(options.staggerMs * waveIndex);
      }

      await processBatch(batchRows, options, runtime);
    })();
  });

  try {
    await Promise.all(batchPromises);
  } catch (error) {
    await Promise.allSettled(batchPromises);
    throw error;
  }
}

async function run(options) {
  if (!process.env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY is required');
  }

  const { checkpointRows, bootstrappedLegacyCount, createdCheckpoint } = await initializeCheckpoint(options);
  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  const pendingRows = checkpointRows
    .filter((row) => row.row_idx >= options.startRow)
    .filter((row) => row.status !== STATUS_COMPLETED)
    .slice(0, options.limit ?? undefined);

  console.log(`Source: ${options.sourcePath}`);
  console.log(`Checkpoint: ${options.checkpointPath}`);
  console.log(`Output: ${options.outputPath}`);
  console.log(`Checkpoint created: ${createdCheckpoint ? 'yes' : 'no'}`);
  console.log(`Bootstrapped from legacy output: ${bootstrappedLegacyCount}`);
  console.log(`Dataset rows: ${checkpointRows.length}`);
  console.log(`Pending rows this run: ${pendingRows.length}`);

  if (pendingRows.length === 0) {
    console.log('Nothing to process.');
    return;
  }

  const persistQueue = createPersistQueue(checkpointRows, options.checkpointPath, options.outputPath);
  const progressBar = createProgressBar(pendingRows.length, checkpointRows);
  const rowBatches = chunkRows(pendingRows, options.batchSize);
  const totalBatches = rowBatches.length;
  const totalRequestWaves = Math.ceil(totalBatches / options.requestBatchSize);

  const state = {
    processed: 0,
    completed: checkpointRows.filter((row) => row.status === STATUS_COMPLETED).length,
    datasetTotal: checkpointRows.length,
    failed: checkpointRows.filter((row) => row.status === STATUS_FAILED).length,
    retries: 0,
    batchIndex: 0,
    totalBatches,
  };

  console.log(`Row batches this run: ${totalBatches}`);
  console.log(`Request waves this run: ${totalRequestWaves}`);

  try {
    for (let offset = 0; offset < rowBatches.length; offset += options.requestBatchSize) {
      const batchWave = rowBatches.slice(offset, offset + options.requestBatchSize);
      await processBatchWave(batchWave, options, { client, persistQueue, progressBar, state });
    }
  } finally {
    await persistQueue.flush();
    progressBar.stop();
  }

  console.log(`Completed ${state.processed} rows in ${state.totalBatches} batches.`);
}

export async function runCli(argv = process.argv.slice(2)) {
  const options = parseArgs(argv);
  if (options.help) {
    printHelp();
    return;
  }
  await run(options);
}

const entryHref = process.argv[1] ? pathToFileURL(path.resolve(process.argv[1])).href : null;

if (entryHref && import.meta.url === entryHref) {
  runCli().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
