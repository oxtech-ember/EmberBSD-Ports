$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/pages/onboarding.js
+++ src/renderer/pages/onboarding.js
@@ -82,7 +82,7 @@
     // disabled where the OS registration is unavailable (dev runs, Linux).
     const confirmed = state.defaultSet;
     setDefaultBtn.disabled = confirmed || !state.canSetDefault;
-    setDefaultBtn.textContent = confirmed ? 'Blanc is your default' : 'Set as default';
+    setDefaultBtn.textContent = confirmed ? 'Ember Browser is your default' : 'Set as default';
     dialog.style.setProperty('--ob-default-bg', confirmed || !state.canSetDefault ? 'var(--surface-raised)' : 'var(--accent)');
     dialog.style.setProperty('--ob-default-text', confirmed || !state.canSetDefault ? 'var(--text-dim)' : 'var(--surface-raised)');
     dialog.style.setProperty('--ob-default-border', confirmed || !state.canSetDefault ? 'var(--border)' : 'var(--accent)');
