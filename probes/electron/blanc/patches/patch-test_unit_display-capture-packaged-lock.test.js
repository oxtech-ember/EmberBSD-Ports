$NetBSD$

Select the pinned generic Electron capture runtime on NetBSD.
Keep all runtime and permission bytes unchanged. The NetBSD baseline
identifies imported source; it does not claim multimedia acceptance.
Origin: EmberBSD (AI-assisted), based on Blanc v1.25.0; not submitted upstream.

--- test/unit/display-capture-packaged-lock.test.js.orig
+++ test/unit/display-capture-packaged-lock.test.js
@@ -8,7 +8,7 @@
 const root = path.resolve(__dirname, '../..');
 const readMember = member => fs.readFileSync(path.join(root, member));
 
-for (const platform of ['darwin','win32','linux']) {
+for (const platform of ['darwin','win32','linux','netbsd']) {
   test(`package gate verifies ${platform} runtime and rejects a substituted helper`, () => {
     const result = verifyCaptureRuntime(readMember, platform);
     assert.equal(result.platform, platform);
@@ -34,7 +34,7 @@
 
 test('a shared relay change reopens every platform instead of silently carrying forward passes', () => {
   const changed = member => member === 'src/main/display-capture-ice.js' ? Buffer.from('changed relay') : readMember(member);
-  for (const platform of ['darwin','win32','linux']) {
+  for (const platform of ['darwin','win32','linux','netbsd']) {
     assert.throws(() => verifyCaptureRuntime(changed, platform), /shared capture dependency drift/);
   }
 });
