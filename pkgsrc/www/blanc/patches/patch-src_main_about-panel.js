$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/about-panel.js
+++ src/main/about-panel.js
@@ -1,6 +1,6 @@
 const path = require('node:path');
 
-const ABOUT_APPLICATION_NAME = 'Blanc';
+const ABOUT_APPLICATION_NAME = 'Ember Browser';
 const ABOUT_WEBSITE = 'https://blancbrowser.com';
 const ABOUT_COPYRIGHT = '© 2026 Bananify';
 
@@ -9,10 +9,10 @@
     applicationName: ABOUT_APPLICATION_NAME,
     applicationVersion: app.getVersion(),
     copyright: ABOUT_COPYRIGHT,
-    credits: 'Independent browser by Bananify.',
+    credits: 'Based on Blanc by Bananify.',
     authors: ['Bananify'],
     website: ABOUT_WEBSITE,
-    iconPath: iconPath ?? path.join(__dirname, '../renderer/pages/icon-sunrise.png'),
+    iconPath: iconPath ?? path.join(__dirname, '../renderer/pages/ember-browser.png'),
   };
 }
 
