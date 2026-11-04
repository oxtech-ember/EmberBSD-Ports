$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/workspace-ui.js
+++ src/renderer/workspace-ui.js
@@ -9,13 +9,13 @@
     'limit': 'You have 25 workspaces. Delete one before adding another.',
     'not-patron': 'Creating workspaces needs Blanc Patron.',
     'not-found': 'That workspace is no longer available.',
-    'read-failed': 'Couldn’t read your workspace file. Restart Blanc after checking that the file is accessible.',
+    'read-failed': 'Couldn’t read your workspace file. Restart Ember Browser after checking that the file is accessible.',
     'storage-failed': 'Couldn’t save changes. Check available disk space and try again.',
-    'future-format': 'These workspaces need a newer version of Blanc. Your saved file has not been changed.',
+    'future-format': 'These workspaces need a newer version of Ember Browser. Your saved file has not been changed.',
     'repair-failed': 'Couldn’t preserve a recovery copy. Your workspace file has not been changed.',
     'busy': 'Another workspace action is still finishing. Try again.',
     'activation-failed': 'Couldn’t open the workspace. Your current pages are still available.',
-    'saved-not-opened': 'The workspace was saved, but Blanc couldn’t open it. It remains in your workspace list.',
+    'saved-not-opened': 'The workspace was saved, but Ember Browser couldn’t open it. It remains in your workspace list.',
   };
   function create({ document: doc, window: win, api, popup, list, trigger, label, feedback, onOpenChange }) {
     let data = { items: [], deleted: [], patronActive: false, status: 'saved' };
