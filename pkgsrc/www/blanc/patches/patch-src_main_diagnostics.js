$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/diagnostics.js
+++ src/main/diagnostics.js
@@ -91,8 +91,8 @@
   try {
     const date = new Date().toISOString().slice(0, 10);
     const picked = await dialog.showSaveDialog(parent ?? undefined, {
-      title: 'Export Blanc diagnostics',
-      defaultPath: path.join(app.getPath('downloads'), `Blanc-Diagnostics-${date}.json`),
+      title: 'Export Ember Browser diagnostics',
+      defaultPath: path.join(app.getPath('downloads'), `Ember Browser-Diagnostics-${date}.json`),
       filters: [{ name: 'JSON', extensions: ['json'] }],
     });
     if (picked.canceled || !picked.filePath) return { ok: false, cancelled: true };
