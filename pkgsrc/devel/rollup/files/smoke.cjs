// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
// Functional native-addon consumer. This is not a memory-instrumented test.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');

async function main() {
  const [source, binding, base, work] = process.argv.slice(2);
  assert.equal(process.argv.length, 6, 'expected module, binding, N-API base and work directory');
  assert.match(base, /^[a-z0-9]+(?:-[a-z0-9]+)+$/);
  for (const input of [source, binding, work]) assert.ok(path.isAbsolute(input));
  fs.mkdirSync(work, { recursive: true });
  const temporary = fs.mkdtempSync(path.join(work, 'rollup-smoke-'));
  try {
    const moduleRoot = path.join(temporary, 'module');
    fs.cpSync(source, moduleRoot, { recursive: true });
    const installedBinding = path.join(moduleRoot, 'dist', `rollup.${base}.node`);
    fs.copyFileSync(binding, installedBinding);
    const rollup = require(moduleRoot);
    assert.equal(rollup.VERSION, '4.65.1');
    const native = require(path.join(moduleRoot, 'dist/native.js'));
    const input = 'export const value = 21 * 2;';
    const parsed = native.parse(input, false, false);
    assert.ok(parsed instanceof Uint8Array && parsed.length > 0);
    const asynchronous = await Promise.all(Array.from({ length: 20 }, () => native.parseAsync(input, false, false)));
    for (const result of asynchronous) assert.deepEqual(result, parsed);
    assert.equal(typeof native.xxhashBase64Url(Buffer.from(input)), 'string');
    const entry = path.join(temporary, 'entry.js');
    const dependency = path.join(temporary, 'dependency.js');
    fs.writeFileSync(dependency, 'export const half = 21;\n');
    fs.writeFileSync(entry, "import { half } from './dependency.js'; export const value = half * 2;\n");
    const bundle = await rollup.rollup({ input: entry });
    try {
      const result = await bundle.generate({ format: 'cjs', sourcemap: true });
      assert.equal(result.output.length, 2);
      assert.equal(result.output[1].type, 'asset');
      assert.ok(result.output[0].map);
      assert.ok(result.output[0].map.sources.some(source => source.endsWith('entry.js')));
      assert.ok(result.output[0].map.sources.some(source => source.endsWith('dependency.js')));
      const exports = {};
      vm.runInNewContext(result.output[0].code, { exports, module: { exports } });
      assert.equal(exports.value, 42);
    } finally {
      await bundle.close();
    }
    fs.writeFileSync(entry, 'export const = ;\n');
    await assert.rejects(rollup.rollup({ input: entry }), error => error.code === 'PARSE_ERROR');
    // An existing but invalid local addon must retain upstream's dlopen error;
    // it must not be silently replaced by another optional npm binary.
    const corruptRoot = path.join(temporary, 'corrupt-module');
    fs.cpSync(source, corruptRoot, { recursive: true });
    fs.writeFileSync(path.join(corruptRoot, 'dist', `rollup.${base}.node`), 'invalid native addon');
    const failure = spawnSync(process.execPath, ['-e', 'require(process.argv[1])', path.join(corruptRoot, 'dist/native.js')], {
      encoding: 'utf8', timeout: 10000, env: { ...process.env, NODE_PATH: '' }
    });
    assert.notEqual(failure.status, 0);
    assert.match(failure.stderr, /ERR_DLOPEN_FAILED/);
    console.log('Rollup native parse/async/hash/bundle/error consumers passed.');
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
