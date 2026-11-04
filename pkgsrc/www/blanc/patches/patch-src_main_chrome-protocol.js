$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/chrome-protocol.js
+++ src/main/chrome-protocol.js
@@ -41,7 +41,7 @@
 const SHARED_ASSETS = new Set([
   '/styles.css',
   '/panel-left.svg',
-  '/pages/sunrise-favicon-mark.png',
+  '/pages/ember-browser.svg',
   '/pages/inter-latin.woff2',
   '/pages/instrument-sans-latin-wdth-normal.woff2',
   '/pages/jetbrains-mono-latin.woff2',
@@ -86,7 +86,7 @@
     // pages.js, loads the same two files.
     ['/pages/bangs.js', 'pages/bangs.js'],
     ['/pages/bangs-catalog.js', 'pages/bangs-catalog.js'],
-    ['/sunrise-hero-mark.png', 'sunrise-hero-mark.png'],
+    
     // Pure close-on-leave policy for a hover-opened panel. No IPC and no
     // application data.
     ['/hover-panel-leave.js', 'hover-panel-leave.js'],
