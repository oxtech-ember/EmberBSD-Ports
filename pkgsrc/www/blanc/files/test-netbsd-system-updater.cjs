'use strict';
// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'netbsd-system-updater.js'), 'utf8');
function load(parent) {
  const calls = [];
  const requested = [];
  const electron = { app: { name: 'Ember Browser' },
    BrowserWindow: { getFocusedWindow: () => parent },
    dialog: { showMessageBox: async (...args) => { calls.push(args); return { response: 0 }; } } };
  const module = { exports: {} };
  vm.runInNewContext(source, { module, console: { info() {} }, require(name) {
    requested.push(name);
    assert.equal(name, 'electron');
    return electron;
  } });
  return { api: module.exports, calls, requested };
}

test('NetBSD updates are described as system packages without loading an updater', async () => {
  for (const parent of [null, { id: 1 }]) {
    const { api, calls, requested } = load(parent);
    api.setupAutoUpdater();
    await api.checkForUpdatesManually();
    assert.deepEqual(requested, ['electron']);
    const options = calls[0].at(-1);
    assert.match(options.message, /system package manager/);
    assert.match(options.detail, /system package manager/);
    assert.equal(calls[0].length, parent ? 2 : 1);
  }
});

test('NetBSD branch is selected before the upstream updater require', () => {
  const main = fs.readFileSync(process.env.EMBER_BROWSER_SOURCE + '/src/main/main.js', 'utf8');
  assert.match(main, /process\.platform === 'netbsd'\s*\? require\('\.\/netbsd-system-updater'\)\s*:\s*require\('\.\/updater'\)/);
});
