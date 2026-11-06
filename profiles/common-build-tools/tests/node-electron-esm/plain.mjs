// SPDX-License-Identifier: BSD-2-Clause
// Run beside a conventional node_modules/electron test package.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import value from 'electron';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
assert.equal(value.marker, 'ordinary-node-package');
assert.equal(require('electron').marker, value.marker);
assert.equal((await import('electron')).default.marker, value.marker);
assert.throws(() => fileURLToPath('electron:electron'),
  { code: 'ERR_INVALID_URL_SCHEME' });
await assert.rejects(import('electron:electron'),
  { code: 'ERR_UNSUPPORTED_ESM_URL_SCHEME' });
await assert.rejects(import('electron/not-a-real-subpath'),
  { code: 'ERR_MODULE_NOT_FOUND' });

// A custom loader cannot opt ordinary Node into the Electron translator.
const { registerHooks } = await import('node:module');
const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === 'custom-electron-format') {
      return { url: 'file:///custom-electron-format', shortCircuit: true };
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url === 'file:///custom-electron-format') {
      return { format: 'electron', source: '', shortCircuit: true };
    }
    return nextLoad(url, context);
  },
});
try {
  await assert.rejects(import('custom-electron-format'),
    { code: 'ERR_UNKNOWN_MODULE_FORMAT' });
} finally {
  hooks.deregister();
}
console.log('plain Node package resolution: PASS');
