import {
	DEFAULT_TEMPLATE,
	buildNoteTemplates,
	type SidebarSection,
	type TabContent
} from './deckTemplate';
import CONSTANTS, { MORE_INFO_SIDEBAR } from './dict/contants';
import { TONE_PRESETS } from './tonePresets';

export interface BundleTemplate {
	ord: number;
	name: string;
	qfmt: string;
	afmt: string;
	req: [number, 'all' | 'any', number[]];
	sidebarSections: { front: SidebarSection[]; back: SidebarSection[] };
	defaultOff: { front: string[]; back: string[] };
}

export interface BundleModel {
	fields: string[];
	fieldRoles: Record<string, string | string[]>;
	templates: BundleTemplate[];
	css: string;
}

export interface ClassDeckBundleV1 {
	version: 1;
	engine: string;
	models: {
		vocabulary: BundleModel;
		sentence: BundleModel;
		listening: BundleModel;
	};
	media: {
		ankiPersistence: string;
		ankiTts: string;
		hanziWriter: string;
		hanziWriterData: string;
		cedict: string;
		sentences: string;
		sqlWasm: string;
		offlineRuntime: string;
	};
	writerControls: {
		drawSize: { default: number; min: number; max: number };
		strokeSize: { default: number; min: number; max: number };
		hintMisses: { default: number; min: number; max: number };
	};
	tonePalettes: typeof TONE_PRESETS;
}

const VOCABULARY_FIELDS = [
	'Chinese',
	'Traditional',
	'Pinyin',
	'Meaning',
	'Example',
	'ExampleTranslation',
	'Image',
	'Audio',
	'ClassDate',
	'SourceRef',
	'Zhuyin',
	'PartOfSpeech',
	'Definitions',
	'Breakdown',
	'Radical',
	'HskLevel',
	'Frequency'
] as const;

const SENTENCE_FIELDS = [
	'Chinese',
	'Pinyin',
	'Meaning',
	'Answer',
	'Explanation',
	'Audio',
	'ClassDate',
	'SourceRef'
] as const;

const LISTENING_FIELDS = ['Chinese', 'Pinyin', 'Meaning', 'Audio', 'ClassDate', 'SourceRef'] as const;

const MEDIA: ClassDeckBundleV1['media'] = {
	ankiPersistence: 'cdx1-anki-persistence.js',
	ankiTts: 'cdx1-anki-tts.js',
	hanziWriter: 'cdx1-hanzi-writer.min.js',
	hanziWriterData: 'cdx1-hanzi-writer-data.json',
	cedict: 'cdx1-cedict.db.zip',
	sentences: 'cdx1-hsk-sentences.db.zip',
	sqlWasm: 'cdx1-sql-wasm.wasm',
	offlineRuntime: 'cdx1-offline-runtime.js'
};

const OFFLINE_STUDY = `
<details class="cdx1-study"><summary>Offline dictionary & examples</summary>
<span id="cdx1-query" hidden>{{Chinese}}</span>
<button type="button" onclick="cdx1Dictionary()">Dictionary</button>
<button type="button" onclick="cdx1Examples(0)">Examples</button>
<div id="cdx1-results" class="cdx1-results"></div>
</details>
<script src="cdx1-offline-runtime.js"></script>
<script>
async function cdx1Dictionary(){var q=document.getElementById('cdx1-query').textContent;var r=await CDX1Offline.searchDictionary(q,20);document.getElementById('cdx1-results').innerHTML=r.html;}
async function cdx1Examples(offset){var q=document.getElementById('cdx1-query').textContent;var r=await CDX1Offline.loadExamplePage(q,offset||0,10);var e=document.getElementById('cdx1-results');e.innerHTML=(offset?e.innerHTML:'')+r.html;var b=e.querySelector('[data-offset]');if(b)b.onclick=function(){cdx1Examples(Number(b.dataset.offset));};}
</script>`;

const ENGINE_FIELDS = [
	'Simplified',
	'Traditional',
	'Pinyin',
	'Zhuyin',
	'PartOfSpeech',
	'SimpleMeaning',
	'Definitions',
	'Breakdown',
	'Radical',
	'HskLevel',
	'Frequency',
	'Examples',
	'Audio'
];

const fullBack = [
	'backSimplified',
	'backTraditional',
	'backPinyin',
	'backZhuyin',
	'backPartOfSpeech',
	'backSimpleMeaning',
	'backDefinitions',
	'backBreakdown',
	'backRadical',
	'backHskLevel',
	'backFrequency',
	'backExamples',
	'backAudio',
	'backControlButtons',
	'backSeparator'
];

const card = (front: string[], back: string[]): TabContent[string] => ({
	front,
	back,
	additional: [],
	elementStyles: {}
});

function vocabularyTabs(): TabContent {
	return {
		Recognize: card(['frontSimplified'], fullBack),
		Produce: card(['frontSimpleMeaning'], fullBack),
		Listen: card(['frontAudio'], fullBack),
		Writing: card(
			['frontSimpleMeaning', 'frontwritingComponent', 'frontControlButtons'],
			[...fullBack, 'backwritingComponent']
		)
	};
}

function replaceField(markup: string, engine: string, model: string): string {
	return markup.replace(new RegExp(`{{([#\\/^]?)${engine}}}`, 'g'), `{{$1${model}}}`);
}

function classFieldMarkup(markup: string): string {
	let out = markup;
	const fields: Record<string, string> = {
		Simplified: 'Chinese',
		Traditional: 'Traditional',
		Pinyin: 'Pinyin',
		Zhuyin: 'Zhuyin',
		PartOfSpeech: 'PartOfSpeech',
		SimpleMeaning: 'Meaning',
		Definitions: 'Definitions',
		Breakdown: 'Breakdown',
		Radical: 'Radical',
		HskLevel: 'HskLevel',
		Frequency: 'Frequency',
		Audio: 'Audio'
	};
	for (const [engine, model] of Object.entries(fields)) out = replaceField(out, engine, model);
	out = out.replace(
		/{{([#\/^]?)Examples}}/g,
		(_match, sigil: string) =>
			sigil
				? `{{${sigil}Example}}`
				: '{{Example}}<div class="example-translation">{{ExampleTranslation}}</div>'
	);
	return out;
}

function removeExternalLookup(markup: string): string {
	return markup
		.replaceAll(MORE_INFO_SIDEBAR, '')
		.replace(/\s*<a class="btn" id='btnMoreOptions'[\s\S]*?<\/a>/g, '');
}

function namespaceRuntime(markup: string): string {
	let out = removeExternalLookup(markup)
		.replaceAll('_anki-persistence.js', MEDIA.ankiPersistence)
		.replaceAll('_hanzi-writer.min.js', MEDIA.hanziWriter)
		.replaceAll('_hanzi-writer-data.json', MEDIA.hanziWriterData)
		.replaceAll(
			'https://cdn.jsdelivr.net/gh/krmanik/anki-tts@latest/src/anki_tts.js',
			MEDIA.ankiTts
		)
		.replace('var defaults = { "draw-size": 400, "stroke-size": 64, "hint-miss": 5 };',
			'var defaults = { "draw-size": 250, "stroke-size": 6, "hint-miss": 5 };');
	out = out.replace(
		/    function btnTapAudio\(\) \{[\s\S]*?\n    \}\n\n    function playAudio/,
		'    function btnTapAudio() {}\n\n    function playAudio'
	);
	return out;
}

function adapt(markup: string): string {
	return classFieldMarkup(namespaceRuntime(markup));
}

function parseSeed<T>(markup: string, name: string, fallback: T): T {
	const match = new RegExp(`var ${name} = (\\[[^;]*\\]);`).exec(markup);
	return match ? (JSON.parse(match[1]) as T) : fallback;
}

function asTemplate(
	ord: number,
	name: string,
	qfmt: string,
	afmt: string,
	req: [number, 'all' | 'any', number[]]
): BundleTemplate {
	return {
		ord,
		name,
		qfmt,
		afmt,
		req,
		sidebarSections: {
			front: parseSeed<SidebarSection[]>(qfmt, 'SIDEBAR_SECTIONS', []),
			back: parseSeed<SidebarSection[]>(afmt, 'SIDEBAR_SECTIONS', [])
		},
		defaultOff: {
			front: parseSeed<string[]>(qfmt, 'defaultOff', []),
			back: parseSeed<string[]>(afmt, 'defaultOff', [])
		}
	};
}

function simpleTemplate(
	ord: number,
	name: string,
	qfmt: string,
	afmt: string,
	req: [number, 'all' | 'any', number[]]
): BundleTemplate {
	return asTemplate(ord, name, qfmt, afmt, req);
}

export function buildClassDeckBundle(): ClassDeckBundleV1 {
	const compiled = buildNoteTemplates({
		fields: [...ENGINE_FIELDS],
		tabContent: vocabularyTabs(),
		includeAudio: true,
		template: DEFAULT_TEMPLATE
	});
	const vocabularyTemplates = compiled.tmpls.map((template, ord) => {
		let qfmt = adapt(template.qfmt);
		let afmt = adapt(template.afmt) + OFFLINE_STUDY;
		if (ord === 2) qfmt = '<div class="audio-only">{{Audio}}</div>';
		const req: [number, 'all', number[]] = [ord, 'all', [ord === 2 ? 7 : 0]];
		return asTemplate(ord, template.name, qfmt, afmt, req);
	});

	const sentenceBack = `<hr><div class="hanzi">{{Chinese}}</div>{{#Answer}}<div class="answer">{{Answer}}</div>{{/Answer}}{{#Pinyin}}<div class="pinyin">{{Pinyin}}</div>{{/Pinyin}}{{#Explanation}}<div class="explanation">{{Explanation}}</div>{{/Explanation}}{{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}`;
	const listeningBack = `<hr><button class="replay" onclick="document.querySelector('#listen-audio a, #listen-audio audio')?.click()">Replay</button><div id="listen-audio" class="audio">{{Audio}}</div><div class="hanzi">{{Chinese}}</div><div class="pinyin">{{Pinyin}}</div>`;

	return {
		version: 1,
		engine: 'xiehanzi-class-deck-v1',
		models: {
			vocabulary: {
				fields: [...VOCABULARY_FIELDS],
				fieldRoles: {
					Simplified: 'Chinese', Traditional: 'Traditional', Pinyin: 'Pinyin',
					SimpleMeaning: 'Meaning', Examples: ['Example', 'ExampleTranslation'], Audio: 'Audio'
				},
				templates: vocabularyTemplates,
				css: compiled.css
			},
			sentence: {
				fields: [...SENTENCE_FIELDS],
				fieldRoles: { Simplified: 'Chinese', Pinyin: 'Pinyin', SimpleMeaning: 'Meaning', Audio: 'Audio' },
				templates: [
					simpleTemplate(0, 'Produce', '<div class="prompt">{{Meaning}}</div>', sentenceBack, [0, 'all', [0]]),
					simpleTemplate(1, 'Listen', '<div class="audio-only">{{Audio}}</div>', sentenceBack, [1, 'all', [5]])
				],
				css: compiled.css
			},
			listening: {
				fields: [...LISTENING_FIELDS],
				fieldRoles: { Simplified: 'Chinese', Pinyin: 'Pinyin', Audio: 'Audio' },
				templates: [simpleTemplate(0, 'Listen', '<div class="audio-only">{{Audio}}</div>', listeningBack, [0, 'all', [3]])],
				css: compiled.css
			}
		},
		media: { ...MEDIA },
		writerControls: {
			drawSize: { default: 250, min: 100, max: 1000 },
			strokeSize: { default: 6, min: 2, max: 50 },
			hintMisses: { default: 5, min: 1, max: 10 }
		},
		tonePalettes: TONE_PRESETS.map((preset) => ({ ...preset, colors: { ...preset.colors } }))
	};
}

export function serializeClassDeckBundle(bundle: ClassDeckBundleV1): string {
	return `${JSON.stringify(bundle, null, 2)}\n`;
}

export const CLASS_DECK_FIELDS = {
	vocabulary: VOCABULARY_FIELDS,
	sentence: SENTENCE_FIELDS,
	listening: LISTENING_FIELDS
};

void CONSTANTS;
