$NetBSD$

Verify that protection changes reload without cached subresources.
Origin: EmberBSD contributors (AI-assisted).

--- /dev/null
+++ test/unit/adblock-settings-reload.test.js
@@ -0,0 +1,26 @@
+'use strict';
+const { test } = require('node:test');
+const assert = require('node:assert/strict');
+const fs = require('node:fs');
+const vm = require('node:vm');
+const source = fs.readFileSync(require('node:path').join(__dirname, '../../src/main/main.js'), 'utf8');
+const match = source.match(/function reloadTabAfterSettingsFanout\(tab\) \{[\s\S]*?\n\}\n/);
+assert.ok(match, 'reload function is present');
+function setup() {
+  const queued = [], calls = [], methods = new Map(), wc = { id: 1, reload: () => calls.push('normal'), reloadIgnoringCache: () => calls.push('bypass') };
+  const tab = { view: {}, wc };
+  const context = { setImmediate: f => queued.push(f), lastMainFrameMethod: methods, liveContents: t => t?.wc };
+  vm.runInNewContext(match[0] + '\nthis.reload = reloadTabAfterSettingsFanout;', context);
+  return { ...context, queued, calls, methods, tab, wc };
+}
+test('settings reload defers and bypasses cache', () => {
+  const s = setup(); s.reload(s.tab);
+  assert.deepEqual(s.calls, []); assert.equal(s.queued.length, 1);
+  s.queued[0](); assert.deepEqual(s.calls, ['bypass']);
+});
+test('POST and closed tabs are not reloaded', () => {
+  const s = setup(); s.methods.set(1, 'POST'); s.reload(s.tab); assert.equal(s.queued.length, 0);
+  s.methods.delete(1); s.reload(s.tab); s.methods.set(1, 'POST'); s.queued.shift()();
+  s.methods.delete(1); s.reload(s.tab); s.tab.wc = null; s.queued.shift()();
+  assert.deepEqual(s.calls, []);
+});
