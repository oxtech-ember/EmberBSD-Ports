$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/pages/settings-sync-setup-model.js
+++ src/renderer/pages/settings-sync-setup-model.js
@@ -102,20 +102,20 @@
       fieldsVisible: !!state.path,
       setupTitle: join ? 'Connect this device' : (start ? 'Start syncing from this device' : 'Set up Sync'),
       setupIntro: join
-        ? 'Use the same sync name and passphrase as your other device. Blanc checks them before saving anything here.'
+        ? 'Use the same sync name and passphrase as your other device. Ember Browser checks them before saving anything here.'
         : (start
-          ? 'Sync your favorites and settings across your devices, and, if you choose, open tabs. Everything is end-to-end encrypted — Blanc can’t read it, and can’t recover it if you forget your passphrase.'
+          ? 'Sync your favorites and settings across your devices, and, if you choose, open tabs. Everything is end-to-end encrypted — Ember Browser can’t read it, and can’t recover it if you forget your passphrase.'
           : 'Sync your favorites and settings across your devices, and, if you choose, open tabs. Everything is end-to-end encrypted.'),
       handleHint: join
         ? 'Enter the exact sync name you used on your other device.'
         : 'A label for your sync, like a username. You’ll type it again on your other devices.',
       passphraseHint: join
         ? 'Enter the exact passphrase. Case matters.'
-        : '16+ characters, or 10+ mixing letters, numbers and symbols. Blanc can’t recover it if you forget it.',
+        : '16+ characters, or 10+ mixing letters, numbers and symbols. Ember Browser can’t recover it if you forget it.',
       submitLabel: join ? 'Connect' : 'Turn on sync',
       finishTitle: join ? 'Connect this device' : 'Turn on Sync',
       finishHint: join
-        ? 'Blanc will look for your encrypted sync before saving these credentials on this device.'
+        ? 'Ember Browser will look for your encrypted sync before saving these credentials on this device.'
         : 'You’re ready — your favorites and settings will sync securely across your devices.',
       submitDisabled: busy(state) || !valid(state),
       showNotFound: state.phase === 'notFound',
