$NetBSD$

Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- index.js.orig
+++ index.js
@@ -1,15 +1,2 @@
-let parts = [process.platform, process.arch];
-if (process.platform === 'linux') {
-  const {MUSL, family} = require('detect-libc');
-  if (family === MUSL) {
-    parts.push('musl');
-  } else if (process.arch === 'arm') {
-    parts.push('gnueabihf');
-  } else {
-    parts.push('gnu');
-  }
-} else if (process.platform === 'win32') {
-  parts.push('msvc');
-}
-
-module.exports = require(`./dprint-node.${parts.join('-')}.node`);
+// Use the native addon built by the selected Ports toolchain.
+module.exports = require("./dprint-node.node");
