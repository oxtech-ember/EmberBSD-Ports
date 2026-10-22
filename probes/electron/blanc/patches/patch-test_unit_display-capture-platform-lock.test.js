$NetBSD$

Select the pinned generic Electron capture runtime on NetBSD.
Keep all runtime and permission bytes unchanged. The NetBSD baseline
identifies imported source; it does not claim multimedia acceptance.
Origin: EmberBSD (AI-assisted), based on Blanc v1.25.0; not submitted upstream.

--- test/unit/display-capture-platform-lock.test.js.orig
+++ test/unit/display-capture-platform-lock.test.js
@@ -9,7 +9,7 @@
 const { chromeResourcePath } = require('../../src/main/chrome-protocol');
 const { captureMainworldSourceForPlatform } = require('../../src/main/capture-mainworld');
 
-for (const platform of ['darwin', 'win32', 'linux']) {
+for (const platform of ['darwin', 'win32', 'linux', 'netbsd']) {
   test(`${platform} selects one complete locked capture runtime`, () => {
     const runtime = captureRuntimeForPlatform(platform);
     assert.equal(runtime.revision, platform === 'darwin' ? 'fda425eb' : 'c26127eb');
@@ -33,7 +33,7 @@
 }
 
 test('runtime selection rejects unsupported platforms and page-supplied values', () => {
-  for (const value of ['', 'darwin/../linux', '__proto__', {platform:'linux'}]) {
+  for (const value of ['', 'freebsd', 'openbsd', 'darwin/../linux', '__proto__', {platform:'linux'}]) {
     assert.throws(() => captureRuntimeForPlatform(value), /Unsupported capture platform/);
   }
 });
