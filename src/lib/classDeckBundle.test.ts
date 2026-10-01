import { describe, expect, it } from 'vitest';
import { buildClassDeckBundle, serializeClassDeckBundle } from './classDeckBundle';

const bundle = () => buildClassDeckBundle();

describe('class deck bundle contract', () => {
	it('emits append-only models and ordinals', () => {
		const value = bundle();
		expect(value.version).toBe(1);
		expect(value.models.vocabulary.fields).toEqual([
			'Chinese', 'Traditional', 'Pinyin', 'Meaning', 'Example', 'ExampleTranslation',
			'Image', 'Audio', 'ClassDate', 'SourceRef', 'Zhuyin', 'PartOfSpeech',
			'Definitions', 'Breakdown', 'Radical', 'HskLevel', 'Frequency'
		]);
		expect(value.models.vocabulary.templates.map((t) => [t.ord, t.name])).toEqual([
			[0, 'Recognize'], [1, 'Produce'], [2, 'Listen'], [3, 'Writing']
		]);
		expect(value.models.sentence.templates.map((t) => [t.ord, t.name])).toEqual([
			[0, 'Produce'], [1, 'Listen']
		]);
		expect(value.models.listening.templates.map((t) => [t.ord, t.name])).toEqual([[0, 'Listen']]);
	});

	it('namespaces every media reference', () => {
		const value = bundle();
		expect(value.media).toEqual({
			ankiPersistence: 'cdx1-anki-persistence.js',
			ankiTts: 'cdx1-anki-tts.js',
			hanziWriter: 'cdx1-hanzi-writer.min.js',
			hanziWriterData: 'cdx1-hanzi-writer-data.json',
			cedict: 'cdx1-cedict.db.zip',
			sentences: 'cdx1-hsk-sentences.db.zip',
			sqlWasm: 'cdx1-sql-wasm.wasm',
			offlineRuntime: 'cdx1-offline-runtime.js'
		});
		const markup = Object.values(value.models)
			.flatMap((model) => model.templates.flatMap((template) => [template.qfmt, template.afmt]))
			.join('\n');
		expect(markup).not.toMatch(/(?:src|fetch\()=["']?_(?:anki|hanzi)/);
		expect(markup).not.toContain('_hanzi-writer.min.js');
		expect(markup).not.toContain('_hanzi-writer-data.json');
	});

	it('keeps offline study controls on vocabulary cards only', () => {
		const value = bundle();
		for (const template of value.models.vocabulary.templates) {
			expect(template.afmt).toContain('cdx1-offline-runtime.js');
			expect(template.afmt).toContain('Offline dictionary & examples');
		}
		for (const model of [value.models.sentence, value.models.listening]) {
			for (const template of model.templates) expect(template.qfmt + template.afmt).not.toContain('cdx1-study');
		}
	});

	it('keeps writer vocabulary only', () => {
		const value = bundle();
		const vocabulary = value.models.vocabulary.templates;
		expect(vocabulary[3].qfmt + vocabulary[3].afmt).toContain('character-target-div');
		for (const model of [value.models.sentence, value.models.listening]) {
			for (const template of model.templates) {
				expect(template.qfmt + template.afmt).not.toContain('character-target-div');
				expect(template.qfmt + template.afmt).not.toContain('HanziWriter');
			}
		}
	});

	it('uses local anki tts without press sound', () => {
		const markup = Object.values(bundle().models)
			.flatMap((model) => model.templates.flatMap((template) => [template.qfmt, template.afmt]))
			.join('\n');
		expect(markup).toContain('cdx1-anki-tts.js');
		expect(markup).not.toContain('cdn.jsdelivr.net');
		expect(markup).not.toContain('_press.mp3');
	});

	it('aligns writer control defaults', () => {
		const controls = bundle().writerControls;
		expect(controls.drawSize).toEqual({ default: 250, min: 100, max: 1000 });
		expect(controls.strokeSize).toEqual({ default: 6, min: 2, max: 50 });
		expect(controls.hintMisses).toEqual({ default: 5, min: 1, max: 10 });
	});

	it('renders Vietnamese production and audio-only listening', () => {
		const value = bundle();
		const production = value.models.vocabulary.templates[1];
		expect(production.qfmt).toContain('{{Meaning}}');
		expect(production.qfmt).not.toContain('{{Chinese}}');
		expect(production.afmt).toContain('{{Chinese}}');

		const listening = value.models.listening.templates[0];
		expect(listening.qfmt.replace(/<[^>]*>/g, '').trim()).toBe('{{Audio}}');
		expect(listening.qfmt).not.toContain('{{Chinese}}');
		expect(listening.qfmt).not.toContain('{{Pinyin}}');
		expect(listening.afmt).toContain('{{Chinese}}');
		expect(listening.afmt).toContain('{{Pinyin}}');
		expect(listening.afmt).not.toContain('{{Meaning}}');
	});

	it('regeneration is byte stable', () => {
		expect(serializeClassDeckBundle(bundle())).toBe(serializeClassDeckBundle(bundle()));
		expect(serializeClassDeckBundle(bundle())).toMatch(/^\{\n  "version": 1,/);
	});
});
