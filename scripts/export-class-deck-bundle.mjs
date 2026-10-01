import { spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const target = resolve(here, '../class_deck/assets/class-deck-bundle.v1.json');
const vitest = resolve(here, '../node_modules/.bin/vitest');
const result = spawnSync(vitest, ['run', 'src/lib/classDeckBundle.export.test.ts'], {
	cwd: resolve(here, '..'),
	stdio: 'inherit',
	env: { ...process.env, CLASS_DECK_BUNDLE_TARGET: target }
});
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
console.log('wrote ' + target);
