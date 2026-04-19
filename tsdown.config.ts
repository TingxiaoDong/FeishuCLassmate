import { defineConfig } from 'tsdown';

export default defineConfig({
  entry: ['index.ts'],
  format: ['esm'],
  target: 'node22',
  outDir: 'dist',
  dts: true,
  clean: true,
  external: ['openclaw', '@larksuite/openclaw-lark'],
});
