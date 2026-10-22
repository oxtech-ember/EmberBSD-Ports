$NetBSD$

Select the pinned generic Electron capture runtime on NetBSD.
Keep all runtime and permission bytes unchanged. The NetBSD baseline
identifies imported source; it does not claim multimedia acceptance.
Origin: EmberBSD (AI-assisted), based on Blanc v1.25.0; not submitted upstream.

--- src/main/capture-platform.js.orig
+++ src/main/capture-platform.js
@@ -25,10 +25,20 @@
   helper: 'display-capture-helper.js',
 });
 
+// NetBSD uses the generic Electron runtime without Linux-specific flags.
+// Changes to these shared files require review for Windows and NetBSD.
+const NETBSD = Object.freeze({
+  revision: 'c26127eb',
+  preload: 'capture-preload.js',
+  broker: 'display-capture-broker.js',
+  helper: 'display-capture-helper.js',
+});
+
 function captureRuntimeForPlatform(platform = process.platform) {
   if (platform === 'darwin') return PLAYOUT;
   if (platform === 'win32') return WINDOWS;
   if (platform === 'linux') return LINUX;
+  if (platform === 'netbsd') return NETBSD;
   throw new Error('Unsupported capture platform');
 }
 
