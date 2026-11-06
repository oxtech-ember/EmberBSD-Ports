// SPDX-License-Identifier: BSD-2-Clause
// Run as an Electron main entry point in a real app context.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { app } from 'electron';

const require = createRequire(import.meta.url);
const cjs = require('electron');
assert.equal(app, cjs.app);
for (const name of ['electron', 'electron/main', 'electron/common',
  'electron/renderer', 'electron/utility']) {
  assert.equal(require(name), cjs);
  const esm = await import(name);
  assert.equal(esm.app, app);
  assert.equal(esm.default, cjs);
}
await assert.rejects(import('electron/not-a-real-subpath'),
  { code: 'ERR_MODULE_NOT_FOUND' });
assert.equal(typeof (await import('node:fs')).readFileSync, 'function');
console.log('electron app ESM aliases: PASS');
app.exit(0);
