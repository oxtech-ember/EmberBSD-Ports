$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/main.js
+++ src/main/main.js
@@ -644,11 +644,11 @@
   if (code === 'empty') return 'This handoff has no eligible web tabs.';
   if (code === 'multiple-active-tabs') return 'The source browser reported more than one active tab.';
   if (code === 'decryption-failed' || code === 'invalid-envelope' || code === 'invalid-payload') {
-    return 'Blanc could not verify this handoff. It may have been changed or opened with the wrong link.';
+    return 'Ember Browser could not verify this handoff. It may have been changed or opened with the wrong link.';
   }
   if (code === 'unavailable') return 'This handoff has expired, was already used, or is unavailable.';
-  if (code === 'offline') return 'Blanc could not reach the tab handoff service. Check your connection and try again.';
-  return 'Blanc could not import these tabs.';
+  if (code === 'offline') return 'Ember Browser could not reach the tab handoff service. Check your connection and try again.';
+  return 'Ember Browser could not import these tabs.';
 }
 
 async function claimTabHandoff(parsed) {
@@ -1138,19 +1138,7 @@
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
@@ -7170,7 +7158,7 @@
         },
         ...(isMac ? [] : [
           { type: 'separator' },
-          { label: 'About Blanc', click: bound(() => showAboutPanel({ app })) },
+          { label: 'About Ember Browser', click: bound(() => showAboutPanel({ app })) },
         ]),
       ],
     },
@@ -7236,8 +7224,8 @@
 
 function profileWindowTitle(profile) {
   return profile?.id === DEFAULT_PROFILE_ID
-    ? 'Blanc'
-    : `${profile?.name ?? 'Profile'} — Blanc`;
+    ? 'Ember Browser'
+    : `${profile?.name ?? 'Profile'} — Ember Browser`;
 }
 
 function createMainWindowForRuntime(runtime, { ensureStartTab = false } = {}) {
@@ -7345,7 +7333,7 @@
         type: 'error',
         buttons: ['OK'],
         message: 'Couldn’t close this window safely',
-        detail: 'Blanc couldn’t save its latest workspace state. Check available disk space and try again.',
+        detail: 'Ember Browser couldn’t save its latest workspace state. Check available disk space and try again.',
       });
     },
   });
@@ -7878,7 +7866,7 @@
     return { ok: false, message: `Type “${profile.name}” exactly to delete this profile.` };
   }
   if (sessionReadOnly) {
-    return { ok: false, message: 'This Blanc build cannot safely remove a newer saved workspace.' };
+    return { ok: false, message: 'This Ember Browser build cannot safely remove a newer saved workspace.' };
   }
   if (profileDeletions.hasPendingProfileDeletion(profile.id) || deletingProfileIds.has(profile.id)) {
     return { ok: true, pending: true, message: 'That profile is already being deleted.' };
