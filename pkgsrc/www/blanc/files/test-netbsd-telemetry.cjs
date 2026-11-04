// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
// Exercise actual settings and telemetry with a fake Electron and transport.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const source = process.env.EMBER_BROWSER_SOURCE;
assert(source && path.isAbsolute(source));
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'ember-telemetry-'));
const originalLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === 'electron') return { app: {
    getPath: () => profile, getVersion: () => '1.46.0', isPackaged: true, on: () => {},
  } };
  return originalLoad.call(this, request, parent, isMain);
};
try {
  const settings = require(path.join(source, 'src/main/settings'));
  const telemetry = require(path.join(source, 'src/main/telemetry'));
  const { bananifyServiceAllowed } = require(path.join(source, 'src/main/bananify-services'));
  assert.equal(settings.getSettings().usagePing, false);
  assert.equal(settings.isFirstRunComplete(), false);
  const posts = [];
  const options = {
    isPackaged: () => true,
    fetchImpl: (url, request) => { posts.push({ url, request }); return Promise.resolve({ ok: true }); },
    getInstallId: () => 'test-id', getVersion: () => '1.46.0', platform: 'netbsd', arch: 'x64',
    getSystemVersion: () => '10', makeSessionId: () => 1, newtabLayouts: [],
  };
  const sender = telemetry.createTelemetrySender(options);
  assert.equal(telemetry.productUsageAllowed({ firstRunComplete: false, usagePing: false, privateTab: false }), false);
  assert.equal(sender.sendLaunchPing(), false);
  // Even a legacy true setting cannot bypass the upstream derivative gate.
  assert.equal(telemetry.productUsageAllowed({ firstRunComplete: true, usagePing: true, privateTab: false }), true);
  assert.equal(sender.sendLaunchPing(), false);
  assert.equal(posts.length, 0);
  const official = telemetry.createTelemetrySender({ ...options, serviceAllowed: url => bananifyServiceAllowed(url, 'Blanc') });
  assert.equal(official.sendLaunchPing(), true);
  assert.equal(posts.length, 1);
  assert.equal(posts[0].url, telemetry.PING_ENDPOINT);
  assert.equal(telemetry.productUsageAllowed({ firstRunComplete: true, usagePing: false, privateTab: false }), false);
  console.log('PASS: fresh defaults and derivative gate, official gate with fake transport');
} finally {
  Module._load = originalLoad;
  fs.rmSync(profile, { recursive: true, force: true });
}
