$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/overlay.js
+++ src/renderer/overlay.js
@@ -1265,7 +1265,7 @@
     const protection = document.createElement('span');
     protection.className = 'site-info-protection';
     protection.textContent = blocked
-      ? `Blanc blocked ${blocked} ${blocked === 1 ? 'request' : 'requests'}`
+      ? `Ember Browser blocked ${blocked} ${blocked === 1 ? 'request' : 'requests'}`
       : 'No blocked requests on this page';
     const settingsButton = document.createElement('button');
     settingsButton.type = 'button';
@@ -1279,7 +1279,7 @@
     card.append(footer);
     islandList.replaceChildren(card);
     islandHint.textContent = info.state === 'certificate-error'
-      ? 'Blanc did not offer a bypass'
+      ? 'Ember Browser did not offer a bypass'
       : 'connection details are supplied by Chromium';
   }
 
