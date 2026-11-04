$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/about-panel.js
+++ src/main/about-panel.js
@@ -1,6 +1,6 @@
 const path = require('node:path');
 
-const ABOUT_APPLICATION_NAME = 'Blanc';
+const ABOUT_APPLICATION_NAME = 'Ember Browser';
 const ABOUT_WEBSITE = 'https://blanc.day';
 const ABOUT_COPYRIGHT = '© 2026 Bananify';
 
@@ -30,7 +30,7 @@
     credits: platform === 'linux' ? t('about.credits') : `${t('about.credits')}\n${engine}`,
     authors: ['Bananify'],
     website: ABOUT_WEBSITE,
-    iconPath: iconPath ?? path.join(__dirname, '../renderer/pages/icon-sunrise.png'),
+    iconPath: iconPath ?? path.join(__dirname, '../renderer/pages/ember-browser.png'),
   };
 }
 
