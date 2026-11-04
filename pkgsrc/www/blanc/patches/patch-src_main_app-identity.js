$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/app-identity.js
+++ src/main/app-identity.js
@@ -2,6 +2,6 @@
 // build.appId aligned; unit coverage fails if packaging and runtime ever drift.
 // The historical Bowser id is intentional so updates and OS identity survive
 // the Blanc rename.
-const APP_ID = 'me.bnfy.bowser';
+const APP_ID = 'org.emberbsd.browser';
 
 module.exports = { APP_ID };
