import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'node:path';

// Node 26 exposes a global localStorage getter that returns undefined unless a
// storage file is configured. Let jsdom provide storage in DOM test workers.
process.env.NODE_OPTIONS = [process.env.NODE_OPTIONS, '--no-experimental-webstorage']
	.filter(Boolean)
	.join(' ');

// Aliases: $lib → src/lib, plus tiny stubs for the SvelteKit `$app/*` modules
// the components import (`base`, `goto`, `page`), so they resolve outside the
// SvelteKit dev server.
const alias = {
	$lib: path.resolve('./src/lib'),
	'$app/paths': path.resolve('./src/test/appPathsStub.ts'),
	'$app/navigation': path.resolve('./src/test/appNavigationStub.ts'),
	'$app/state': path.resolve('./src/test/appStateStub.ts')
};

export default defineConfig({
	resolve: { alias },
	test: {
		projects: [
			// Pure logic — fast, no DOM, no Svelte compilation.
			{
				resolve: { alias },
				test: {
					name: 'node',
					environment: 'node',
					include: ['src/**/*.test.ts'],
					exclude: ['src/**/*.svelte.test.ts']
				}
			},
			// Component / interaction tests — jsdom + compiled Svelte.
			{
				plugins: [svelte({ configFile: false })],
				resolve: { alias, conditions: ['browser'] },
				test: {
					name: 'dom',
					environment: 'jsdom',
					globals: true,
					include: ['src/**/*.svelte.test.ts'],
					setupFiles: ['./src/test/setup.ts']
				}
			}
		]
	}
});
