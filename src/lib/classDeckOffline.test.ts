import { beforeEach, describe, expect, it } from 'vitest';
import {
	loadExamplePage,
	searchDictionary,
	setOfflineFixtures
} from './classDeckOffline';

beforeEach(() => {
	setOfflineFixtures(
		[
			{ simplified: '你好', traditional: '你好', pinyin: 'ni3 hao3', definitions: 'hello; <b>welcome</b>', rank: 10 },
			{ simplified: '后', traditional: '後', pinyin: 'hou4', definitions: 'after', rank: 20 },
			{ simplified: '好', traditional: '好', pinyin: 'hao3', definitions: 'good', rank: 5 }
		],
		[
			{ sentence: '你好！', pinyin: 'nǐ hǎo', translation: '<script>alert(1)</script>', tokens: '你 好' },
			{ sentence: '你好，他很好。', pinyin: 'nǐ hǎo', translation: 'Hello.', tokens: '你 好 他 很 好' },
			{ sentence: '好久不见。', pinyin: 'hǎo jiǔ bú jiàn', translation: 'Long time no see.', tokens: '好 久 不 见' }
		]
	);
});

describe('offline dictionary', () => {
	it('finds simplified, traditional, and pinyin with punctuation normalization', async () => {
		expect((await searchDictionary('你好！', 5)).items[0].simplified).toBe('你好');
		expect((await searchDictionary('後', 5)).items[0].simplified).toBe('后');
		expect((await searchDictionary('nǐ hǎo', 5)).items[0].simplified).toBe('你好');
	});

	it('escapes HTML, bounds results, and preserves an intact empty state', async () => {
		const result = await searchDictionary('你好', 1);
		expect(result.items).toHaveLength(1);
		expect(result.html).toContain('&lt;b&gt;welcome&lt;/b&gt;');
		expect(result.html).not.toContain('<b>welcome</b>');
		const empty = await searchDictionary('不存在', 5);
		expect(empty.items).toEqual([]);
		expect(empty.html).toContain('No dictionary matches');
	});
});

describe('offline examples', () => {
	it('escapes text and paginates with Load more', async () => {
		const first = await loadExamplePage('好！', 0, 1);
		expect(first.items).toHaveLength(1);
		expect(first.hasMore).toBe(true);
		expect(first.html).toContain('Load more');
		expect(first.html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
		const last = await loadExamplePage('好', 2, 2);
		expect(last.hasMore).toBe(false);
	});

	it('returns usable empty markup', async () => {
		const result = await loadExamplePage('不存在', 0, 5);
		expect(result.items).toEqual([]);
		expect(result.html).toContain('No example sentences');
	});
});
