$NetBSD$

Select the NetBSD package updater and independent browser profile.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/main.js
+++ src/main/main.js
@@ -154,7 +154,9 @@
   requestNativeMediaAccess: nativeMediaAccess.request,
   nativeMediaAccessState: nativeMediaAccess.state,
 };
-const { setupAutoUpdater, checkForUpdatesManually } = require('./updater');
+const { setupAutoUpdater, checkForUpdatesManually } = process.platform === 'netbsd'
+  ? require('./netbsd-system-updater')
+  : require('./updater');
 const {
   sendLaunchPing,
   sendMahjongPlay,
@@ -1515,19 +1517,7 @@
   app.setPath('userData', `${app.getPath('userData')}-Dev`);
 }
 
-// One-time migration for existing installs: userData's location is
-// derived from productName, so the Bowser -> Blanc rename would otherwise
-// start every existing user on an empty profile. Copy the old directory
-// forward exactly once, before anything (JsonStores, adblock cache,
-// single-instance lock) touches the new one.
-if (app.isPackaged) {
-  const oldUserDataDir = path.join(app.getPath('appData'), 'Bowser');
-  const newUserDataDir = app.getPath('userData');
-  if (!fs.existsSync(newUserDataDir) && fs.existsSync(oldUserDataDir)) {
-    fs.cpSync(oldUserDataDir, newUserDataDir, { recursive: true });
-  }
-}
-
+// The derivative uses its own profile and does not import other applications.
 // Snapshot whether this is a genuinely new Blanc profile before Chromium's
 // ready phase creates its own directories. settings.json is not sufficient:
 // old versions did not write it until a setting changed, while session.json
@@ -13183,8 +13173,8 @@
 
 function profileWindowTitle(profile) {
   return profile?.id === DEFAULT_PROFILE_ID
-    ? 'Blanc'
-    : `${profile?.name ?? mainI18n.t('profile.unnamed')} — Blanc`;
+    ? 'Ember Browser'
+    : `${profile?.name ?? mainI18n.t('profile.unnamed')} — Ember Browser`;
 }
 
 // `inactive`: shown without taking focus (a background routed link, #1199).
