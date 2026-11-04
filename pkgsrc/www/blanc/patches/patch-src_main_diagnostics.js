$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/diagnostics.js
+++ src/main/diagnostics.js
@@ -92,7 +92,7 @@
     const date = new Date().toISOString().slice(0, 10);
     const picked = await dialog.showSaveDialog(parent ?? undefined, {
       title: t('diagnostics.export.title'),
-      defaultPath: path.join(app.getPath('downloads'), `Blanc-Diagnostics-${date}.json`),
+      defaultPath: path.join(app.getPath('downloads'), `Ember Browser-Diagnostics-${date}.json`),
       filters: [{ name: 'JSON', extensions: ['json'] }],
     });
     if (picked.canceled || !picked.filePath) return { ok: false, cancelled: true };
