$NetBSD$

Select the pinned generic Electron capture runtime on NetBSD.
Keep all runtime and permission bytes unchanged. The NetBSD baseline
identifies imported source; it does not claim multimedia acceptance.
Origin: EmberBSD (AI-assisted), based on Blanc v1.25.0; not submitted upstream.

--- /dev/null
+++ test/unit/display-capture-netbsd.test.js
@@ -0,0 +1,93 @@
+'use strict';
+// Origin: EmberBSD (AI-assisted). Downstream source/startup contract only.
+const assert = require('node:assert/strict');
+const test = require('node:test');
+const path = require('node:path');
+const { spawnSync } = require('node:child_process');
+
+const ROOT = path.resolve(__dirname, '../..');
+const CHILD = String.raw`
+  'use strict';
+  const assert = require('node:assert/strict');
+  const fs = require('node:fs');
+  const path = require('node:path');
+  const crypto = require('node:crypto');
+  const root = process.argv[1];
+  // Change the actual runtime property before the capture modules load.
+  // The product never changes process.platform.
+  Object.defineProperty(process, 'platform', { value: 'netbsd' });
+  assert.equal(process.platform, 'netbsd');
+  const { captureRuntimeForPlatform } = require(path.join(root, 'src/main/capture-platform'));
+  const runtime = captureRuntimeForPlatform();
+  assert.deepEqual(runtime, {
+    revision: 'c26127eb',
+    preload: 'capture-preload.js',
+    broker: 'display-capture-broker.js',
+    helper: 'display-capture-helper.js',
+  });
+  assert.ok(Object.isFrozen(runtime));
+  assert.notEqual(runtime, captureRuntimeForPlatform('win32'));
+  const mainworld = require(path.join(root, 'src/main/capture-mainworld'));
+  assert.equal(mainworld.CAPTURE_MAINWORLD_SOURCE,
+    mainworld.captureMainworldSourceForPlatform('netbsd'));
+  const broker = require(path.join(root, 'src/main', runtime.broker));
+  for (const member of ['createHelperAuthority', 'createHelperSession',
+    'attachHelperWindow', 'installDisplayCaptureBroker']) {
+    assert.equal(typeof broker[member], 'function', member);
+  }
+  const { chromeResourcePath } = require(path.join(root, 'src/main/chrome-protocol'));
+  assert.equal(chromeResourcePath('blanc-chrome://display-capture-helper/display-capture-helper.js'),
+    path.join(root, 'src/renderer', runtime.helper));
+  for (const suffix of ['display-capture-helper-linux.js', 'display-capture-helper-playout.js',
+    'display-capture-helper.js?platform=linux']) {
+    assert.equal(chromeResourcePath('blanc-chrome://display-capture-helper/' + suffix), null);
+  }
+  const readMember = member => fs.readFileSync(path.join(root, member));
+  const lock = JSON.parse(readMember('src/main/capture-runtime-lock.json'));
+  assert.equal(lock.baselines.netbsd, runtime.revision);
+  const roles = {};
+  for (const [role, directory] of [['preload', 'main'], ['broker', 'main'], ['helper', 'renderer']]) {
+    const member = 'src/' + directory + '/' + runtime[role];
+    assert.equal(crypto.createHash('sha256').update(readMember(member)).digest('hex'), lock.files[member]);
+    roles[role] = member;
+  }
+  const { verifyCaptureRuntime } = require(path.join(root, 'scripts/verify-packaged-capture-runtime'));
+  assert.deepEqual(verifyCaptureRuntime(readMember, process.platform).members, Object.values(roles));
+  for (const member of Object.values(roles)) {
+    assert.throws(() => verifyCaptureRuntime(
+      candidate => candidate === member ? Buffer.from('changed role') : readMember(candidate), process.platform),
+      /capture runtime drift/);
+  }
+  assert.throws(() => verifyCaptureRuntime(
+    member => member === 'src/main/permissions.js' ? Buffer.from('changed permission') : readMember(member),
+    process.platform), /shared capture dependency drift/);
+  for (const changed of ['src/main/capture-platform.js', 'src/main/capture-runtime-lock.json']) {
+    assert.throws(() => verifyCaptureRuntime(
+      member => member === changed ? Buffer.from('changed dispatch') : readMember(member),
+      process.platform), /dispatch mismatch/);
+  }
+  const flags = require(path.join(root, 'src/main/display-capture-flags'));
+  assert.deepEqual(flags.captureDisabledFeatures(process.platform), []);
+  let switches = 0;
+  assert.equal(flags.applyLinuxCaptureOzone({
+    hasSwitch: () => false,
+    appendSwitch: () => { switches += 1; },
+  }, { platform: process.platform, env: { XDG_SESSION_TYPE: 'wayland', WAYLAND_DISPLAY: 'wayland-0' } }), false);
+  assert.equal(switches, 0);
+  process.stdout.write(JSON.stringify({ platform: process.platform, revision: runtime.revision, roles,
+    sharedLocks: Object.keys(lock.sharedFiles).length, permissionGate: 'unchanged', mediaAcceptance: 'not tested' }));
+`;
+
+test('NetBSD capture bootstrap loads every pinned generic role in an isolated platform child', () => {
+  const child = spawnSync(process.execPath, ['-e', CHILD, ROOT], {
+    cwd: ROOT,
+    env: { ...process.env, NODE_OPTIONS: '' },
+    encoding: 'utf8',
+    timeout: 30_000,
+  });
+  assert.equal(child.status, 0, child.stderr || child.stdout || String(child.error));
+  const result = JSON.parse(child.stdout);
+  assert.equal(result.platform, 'netbsd');
+  assert.equal(result.sharedLocks, 14);
+  assert.equal(result.mediaAcceptance, 'not tested');
+});
