import fsSync from 'node:fs';
import fs from 'node:fs/promises';

/* ---------- READ ---------- */
export async function readJSONL({ filePath, ignoreMissing = false }) {
  if (ignoreMissing && !fsSync.existsSync(filePath)) return [];

  const text = await fs.readFile(filePath, 'utf8');

  const lines = text
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line, i) => {
      try {
        return JSON.parse(line);
      } catch {
        throw new Error(`Invalid JSON at ${filePath}:${i + 1}`);
      }
    });

  return lines;
}

/* ---------- CREATE ---------- */
export async function createJSONL({ filePath, overwrite = false }) {
  if (!overwrite && fsSync.existsSync(filePath)) {
    throw new Error(`File already exists: ${filePath}`);
  }

  await fs.writeFile(filePath, '');
}

/* ---------- WRITE (overwrite whole file) ---------- */
export async function writeJSONL({ filePath, rows }) {
  const data = rows.map((r) => JSON.stringify(r)).join('\n') + '\n';
  await fs.writeFile(filePath, data);
}

/* ---------- APPEND ---------- */
export async function appendJSONL({ filePath, row }) {
  const line = JSON.stringify(row) + '\n';
  await fs.appendFile(filePath, line);
}

/* ---------- VALIDATE ---------- */
export async function validateJSONL({ filePath }) {
  const text = await fs.readFile(filePath, 'utf8');

  const lines = text.split(/\r?\n/);
  let valid = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;

    try {
      JSON.parse(line);
      valid++;
    } catch {
      return {
        valid: false,
        line: i + 1,
        error: `Invalid JSON`,
      };
    }
  }

  return { valid: true, rows: valid };
}
