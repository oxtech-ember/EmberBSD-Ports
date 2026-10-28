'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const [source, provider, wasi] = process.argv.slice(2);
const text = fs.readFileSync(path.join(source, 'build/llhttp.js'), 'utf8');
const start = text.indexOf('const writeWasmChunk = ');
const end = text.indexOf('\n\nlet platform = ', start);
assert.ok(start >= 0 && end > start);
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'undici-wrapper-'));
try {
  for (const name of ['llhttp.wasm', 'llhttp_simd.wasm'])
    fs.copyFileSync(path.join(wasi, name), path.join(directory, name));
  const context = {readFileSync: fs.readFileSync, writeFileSync: fs.writeFileSync,
                   join: path.join, WASM_OUT: directory};
  vm.runInNewContext(text.slice(start, end) + `\nwriteWasmChunk('llhttp.wasm', 'llhttp-wasm.js');\nwriteWasmChunk('llhttp_simd.wasm', 'llhttp_simd-wasm.js');`, context);
  for (const name of ['llhttp-wasm.js', 'llhttp_simd-wasm.js'])
    assert.deepEqual(fs.readFileSync(path.join(provider, 'lib/llhttp', name)), fs.readFileSync(path.join(directory, name)));
  console.log('Undici generated wrappers match upstream generator PASS');
} finally {
  fs.rmSync(directory, {recursive: true, force: true});
}
