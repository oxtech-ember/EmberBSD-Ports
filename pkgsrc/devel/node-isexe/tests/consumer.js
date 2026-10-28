'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const isexe = require(process.argv[2]);
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'isexe-test-'));
(async () => { try {
  const exec = path.join(root, 'executable');
  const plain = path.join(root, 'plain');
  fs.writeFileSync(exec, 'x', {mode: 0o755});
  fs.writeFileSync(plain, 'x', {mode: 0o644});
  assert.equal(isexe.sync(exec), true);
  assert.equal(isexe.sync(plain), false);
  assert.equal(isexe.sync(path.join(root, 'missing'), {ignoreErrors: true}), false);
  assert.equal(await isexe.isexe(exec), true);
  assert.equal(await isexe.isexe(plain), false);
  console.log('isexe common provider consumer PASS');
} finally {
  fs.rmSync(root, {recursive: true, force: true});
} })().catch(error => { console.error(error); process.exitCode = 1; });
