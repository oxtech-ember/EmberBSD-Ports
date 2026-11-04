$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/site-security.js
+++ src/main/site-security.js
@@ -99,7 +99,7 @@
     return {
       state: 'neutral', origin: '', host: '',
       title: 'Connection information unavailable',
-      summary: 'Blanc could not identify this page origin.',
+      summary: 'Ember Browser could not identify this page origin.',
       certificate: null, blockedCount: 0, permissions: [],
     };
   }
@@ -136,7 +136,7 @@
     return { ...base, state: 'insecure', title: 'Connection is not secure', summary: 'Information sent to this site can be read or changed in transit.' };
   }
   if (parsed.protocol === 'blanc:') {
-    return { ...base, state: 'internal', title: 'Blanc page', summary: 'This page is part of Blanc.' };
+    return { ...base, state: 'internal', title: 'Ember Browser page', summary: 'This page is part of Ember Browser.' };
   }
   return { ...base, state: 'neutral', title: 'Connection information', summary: 'This page does not use an HTTP connection.' };
 }
