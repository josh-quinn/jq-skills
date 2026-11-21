import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { remember } from './utils/cache.js';

const NOTES_DIR = (process.env.NOTES_DIR || '~/Meetings').replace('~', os.homedir());
const DB = path.join(os.homedir(), '.notes-mcp', 'notes.json');

export async function listMeetings() {
  const files = await fs.readdir(NOTES_DIR);
  return files.filter((f) => f.endsWith('.json')).map((f) => f.replace(/\.json$/, ''));
}

export async function readTranscript(id) {
  return JSON.parse(await fs.readFile(path.join(NOTES_DIR, `${id}.json`), 'utf8'));
}

export async function saveNote(id, note, context) {
  await fs.mkdir(path.dirname(DB), { recursive: true });
  const db = JSON.parse(await fs.readFile(DB, 'utf8').catch(() => '{}'));
  db[id] = { note, context, savedAt: Date.now() };
  await fs.writeFile(DB, JSON.stringify(db, null, 2));
  await remember(db);
}
