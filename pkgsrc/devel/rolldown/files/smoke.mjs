// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
// Functional native-addon consumer for the source-built Rolldown binding.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { pathToFileURL } from 'node:url';

const [source, binding, base, work] = process.argv.slice(2);
assert.equal(process.argv.length, 6, 'expected module, binding, N-API base and work directory');
assert.match(base, /^[a-z0-9]+(?:-[a-z0-9]+)+$/);
for (const input of [source, binding, work]) assert.ok(path.isAbsolute(input));
fs.mkdirSync(work, { recursive: true });
const temporary = fs.mkdtempSync(path.join(work, 'rolldown-smoke-'));
try {
  const moduleRoot = path.join(temporary, 'node_modules', 'rolldown');
  fs.cpSync(source, moduleRoot, { recursive: true });
  fs.copyFileSync(binding, path.join(moduleRoot, 'dist', 'shared', `rolldown-binding.${base}.node`));
  // ESM ignores NODE_PATH: bind the packaged runtime dependencies explicitly.
  for (const name of ['@rolldown/pluginutils', '@oxc-project/types']) {
    const installed = (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)
      .map(root => path.join(root, name)).find(candidate => fs.existsSync(path.join(candidate, 'package.json')));
    assert.ok(installed, 'missing runtime dependency ' + name);
    fs.mkdirSync(path.dirname(path.join(temporary, 'node_modules', name)), { recursive: true });
    fs.symlinkSync(installed, path.join(temporary, 'node_modules', name), 'dir');
  }
  const rolldown = await import(pathToFileURL(path.join(moduleRoot, 'dist', 'index.mjs')));
  assert.equal(rolldown.VERSION, '1.2.16');
  fs.writeFileSync(path.join(temporary, 'dependency.ts'), 'export function half(n: number): number { return n / 2; }\n');
  fs.writeFileSync(path.join(temporary, 'entry.ts'), "import { half } from './dependency.ts'; export const value = half(84);\n");
  const bundle = await rolldown.rolldown({ input: path.join(temporary, 'entry.ts'), cwd: temporary });
  try {
    const result = await bundle.generate({ format: 'cjs', sourcemap: true });
    const chunk = result.output.find(item => item.type === 'chunk');
    assert.ok(chunk.map.sources.some(name => name.endsWith('dependency.ts')));
    const exports = {};
    vm.runInNewContext(chunk.code, { exports, module: { exports } });
    assert.equal(exports.value, 42);
  } finally {
    await bundle.close();
  }
  fs.writeFileSync(path.join(temporary, 'entry.ts'), 'export const = ;\n');
  await assert.rejects(rolldown.rolldown({ input: path.join(temporary, 'entry.ts'), cwd: temporary }).then(b => b.generate({})));
  console.log('Rolldown native bundle/sourcemap/TypeScript/error consumers passed.');
} finally {
  fs.rmSync(temporary, { recursive: true, force: true });
}
