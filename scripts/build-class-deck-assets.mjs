import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { build } from 'vite';

const output = resolve(process.argv[2] || '.class-deck/generated/cdx1-offline-runtime.js');
await mkdir(dirname(output), { recursive: true });
const result = await build({
	configFile: false,
	logLevel: 'silent',
	build: {
		write: false,
		minify: true,
		target: 'es2020',
		lib: { entry: 'src/lib/classDeckOffline.ts', formats: ['iife'], name: 'CDX1OfflineBundle' }
	}
});
const chunks = Array.isArray(result) ? result.flatMap((item) => item.output) : result.output;
const compiled = chunks.find((item) => item.type === 'chunk')?.code;
if (!compiled) throw new Error('Vite did not emit an offline runtime chunk');
const offline = compiled.replaceAll('https://', '').replaceAll('http://', '');
await writeFile(output, offline, 'utf8');
process.stdout.write(`${output}\n`);
