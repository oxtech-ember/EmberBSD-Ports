// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const {createRequire} = require('node:module');
const {pathToFileURL} = require('node:url');
const root = path.resolve(process.argv[2]);
const load = createRequire(path.join(root, 'probe.cjs'));
const brace = load('brace-expansion');
assert.deepEqual(brace.expand('file{a,{b,c}}.js'), ['filea.js', 'fileb.js', 'filec.js']);
assert.deepEqual(brace.expand('n{1..3}'), ['n1', 'n2', 'n3']);
assert.deepEqual(brace.expand('unclosed{brace'), ['unclosed{brace']);
function check(minimatch) {
  assert.equal(minimatch('foo/a/x.js', 'foo/**/x.{js,ts}'), true);
  assert.equal(minimatch('foo/a/x.ts', 'foo/**/x.{js,ts}'), true);
  assert.equal(minimatch('foo/a/x.txt', 'foo/**/x.{js,ts}'), false);
  assert.equal(minimatch('foo/.hidden', 'foo/*'), false);
}
check(load('minimatch').minimatch);
import(pathToFileURL(path.join(root, 'node_modules/minimatch/dist/esm/index.js')).href)
  .then(module => { check(module.minimatch); console.log('common glob CJS/ESM and brace expansion PASS'); })
  .catch(error => { console.error(error); process.exitCode = 1; });
