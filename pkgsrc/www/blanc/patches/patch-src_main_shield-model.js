$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/shield-model.js
+++ src/main/shield-model.js
@@ -74,20 +74,20 @@
 function shieldChipState({ url, blockedCount, excepted, adblockEnabled }) {
   if (!blockableHostname(url)) return { mode: 'hidden', count: 0, title: '' };
   if (excepted) {
-    return { mode: 'off', count: 0, title: 'Blanc Blocker off for this site — click for site controls' };
+    return { mode: 'off', count: 0, title: 'Ember Browser Blocker off for this site — click for site controls' };
   }
   if (!adblockEnabled) {
-    return { mode: 'off', count: 0, title: 'Blanc Blocker is off everywhere — click for details' };
+    return { mode: 'off', count: 0, title: 'Ember Browser Blocker is off everywhere — click for details' };
   }
   const blocked = blockedCount ?? 0;
   if (blocked > 0) {
     return {
       mode: 'count',
       count: blocked,
-      title: `Blanc Blocker — ${countPhrase(blocked)} blocked here — click for site controls`,
+      title: `Ember Browser Blocker — ${countPhrase(blocked)} blocked here — click for site controls`,
     };
   }
-  return { mode: 'quiet', count: 0, title: 'Blanc Blocker — protected, nothing blocked yet — click for site controls' };
+  return { mode: 'quiet', count: 0, title: 'Ember Browser Blocker — protected, nothing blocked yet — click for site controls' };
 }
 
 // `connection` arrives already derived (main.js does it once per broadcast) and
