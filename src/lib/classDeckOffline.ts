import initSqlJs from 'sql.js';
import { unzip } from 'unzipit';

export interface DictionaryRow {
	simplified: string;
	traditional: string;
	pinyin: string;
	definitions: string;
	rank: number | null;
}

export interface ExampleRow {
	sentence: string;
	pinyin: string;
	translation: string;
	tokens: string;
}

export interface RenderedPage<T> {
	items: T[];
	html: string;
	hasMore: boolean;
}

let dictionaryFixture: DictionaryRow[] | null = null;
let exampleFixture: ExampleRow[] | null = null;
let dictionaryDb: any = null;
let examplesDb: any = null;

export function setOfflineFixtures(dictionary: DictionaryRow[], examples: ExampleRow[]): void {
	dictionaryFixture = dictionary;
	exampleFixture = examples;
}

function escapeHtml(value: unknown): string {
	return String(value ?? '')
		.replaceAll('&', '&amp;')
		.replaceAll('<', '&lt;')
		.replaceAll('>', '&gt;')
		.replaceAll('"', '&quot;')
		.replaceAll("'", '&#39;');
}

function normalizeQuery(value: string): string {
	return (value ?? '').normalize('NFC').trim().replace(/[，。！？!?；;、（）()【】\[\]“”"']/g, '');
}

function normalizePinyin(value: string): string {
	return normalizeQuery(value)
		.normalize('NFD')
		.toLowerCase()
		.replace(/u\u0308/g, 'v')
		.replace(/[\u0300-\u036f]/g, '')
		.replace(/[1-5\s'’·-]+/g, '');
}

async function openZipDatabase(filename: string): Promise<any> {
	const SQL = await initSqlJs({ locateFile: () => 'cdx1-sql-wasm.wasm' });
	const response = await fetch(filename);
	if (!response.ok) throw new Error(`Offline database missing: ${filename}`);
	const bytes = new Uint8Array(await response.arrayBuffer());
	const { entries } = await unzip(bytes);
	const key = Object.keys(entries).find((name) => name.endsWith('.db'));
	if (!key) throw new Error(`No database in ${filename}`);
	return new SQL.Database(new Uint8Array(await entries[key].arrayBuffer()));
}

async function loadDictionaryRows(): Promise<DictionaryRow[]> {
	if (dictionaryFixture) return dictionaryFixture;
	dictionaryDb ??= await openZipDatabase('cdx1-cedict.db.zip');
	dictionaryDb.run('CREATE INDEX IF NOT EXISTS idx_cedict_simplified ON cedict(simplified)');
	const result = dictionaryDb.exec(
		'SELECT simplified, traditional, pinyin, definitions, rank FROM cedict'
	)[0];
	if (!result) return [];
	return result.values.map((row: any[]) => ({
		simplified: String(row[0] ?? ''), traditional: String(row[1] ?? ''),
		pinyin: String(row[2] ?? ''), definitions: String(row[3] ?? ''),
		rank: row[4] == null ? null : Number(row[4])
	}));
}

async function loadExampleRows(): Promise<ExampleRow[]> {
	if (exampleFixture) return exampleFixture;
	examplesDb ??= await openZipDatabase('cdx1-hsk-sentences.db.zip');
	const result = examplesDb.exec('SELECT sentence, pinyin, translation, tokens FROM sentences')[0];
	if (!result) return [];
	return result.values.map((row: any[]) => ({
		sentence: String(row[0] ?? ''), pinyin: String(row[1] ?? ''),
		translation: String(row[2] ?? ''), tokens: String(row[3] ?? '')
	}));
}

function definitionsText(raw: string): string {
	try {
		const parsed = JSON.parse(raw);
		return typeof parsed === 'object' && parsed ? Object.values(parsed).join('; ') : raw;
	} catch {
		return raw;
	}
}

export async function searchDictionary(query: string, limit = 20): Promise<RenderedPage<DictionaryRow>> {
	const clean = normalizeQuery(query);
	const pinyin = normalizePinyin(clean);
	const bounded = Math.max(1, Math.min(50, Math.floor(limit || 20)));
	const rows = (await loadDictionaryRows())
		.filter((row) => row.simplified.includes(clean) || row.traditional.includes(clean) || normalizePinyin(row.pinyin).includes(pinyin))
		.sort((a, b) => (a.rank ?? Number.MAX_SAFE_INTEGER) - (b.rank ?? Number.MAX_SAFE_INTEGER))
		.slice(0, bounded);
	const html = rows.length
		? rows.map((row) => `<article><b>${escapeHtml(row.simplified)}</b> <span>${escapeHtml(row.traditional)}</span><div>${escapeHtml(row.pinyin)}</div><p>${escapeHtml(definitionsText(row.definitions))}</p></article>`).join('')
		: '<div class="cdx1-empty">No dictionary matches.</div>';
	return { items: rows, html, hasMore: false };
}

export async function loadExamplePage(word: string, offset = 0, limit = 10): Promise<RenderedPage<ExampleRow>> {
	const clean = normalizeQuery(word);
	const start = Math.max(0, Math.floor(offset || 0));
	const size = Math.max(1, Math.min(50, Math.floor(limit || 10)));
	const matches = (await loadExampleRows()).filter((row) => row.tokens.includes(clean) || row.sentence.includes(clean));
	const items = matches.slice(start, start + size);
	const hasMore = start + items.length < matches.length;
	let html = items.length
		? items.map((row) => `<article><b>${escapeHtml(row.sentence)}</b><div>${escapeHtml(row.pinyin)}</div><p>${escapeHtml(row.translation)}</p></article>`).join('')
		: '<div class="cdx1-empty">No example sentences.</div>';
	if (hasMore) html += `<button type="button" data-offset="${start + items.length}">Load more</button>`;
	return { items, html, hasMore };
}

if (typeof globalThis !== 'undefined') {
	(globalThis as any).CDX1Offline = { searchDictionary, loadExamplePage };
}
