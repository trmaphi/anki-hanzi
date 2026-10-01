import { mkdir, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { expect, test } from 'vitest';
import { buildClassDeckBundle, serializeClassDeckBundle } from './classDeckBundle';

test.skipIf(!process.env.CLASS_DECK_BUNDLE_TARGET)('exports the deterministic class deck bundle', async () => {
	const target = process.env.CLASS_DECK_BUNDLE_TARGET;
	if (!target) return;
	const serialized = serializeClassDeckBundle(buildClassDeckBundle());
	await mkdir(dirname(target), { recursive: true });
	await writeFile(target, serialized, 'utf8');
	expect(serialized).toBe(serializeClassDeckBundle(buildClassDeckBundle()));
});
