$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/pages/tab-handoff.js
+++ src/renderer/pages/tab-handoff.js
@@ -101,14 +101,14 @@
     const result = await api.accept(newWindow.checked ? 'new-window' : 'current-window');
     if (!result?.ok) {
       if (result?.retryable) {
-        error.textContent = 'Blanc could not open these tabs. Your existing tabs are unchanged. Try again.';
+        error.textContent = 'Ember Browser could not open these tabs. Your existing tabs are unchanged. Try again.';
         error.hidden = false;
         accept.disabled = false;
         newWindow.disabled = false;
       } else showError('This handoff is no longer available.');
     }
   } catch {
-    showError('Blanc could not open this tab set. Try the handoff again.');
+    showError('Ember Browser could not open this tab set. Try the handoff again.');
   } finally {
     cancel.disabled = false;
     updateDestination();
@@ -117,5 +117,5 @@
 
 cancel.addEventListener('click', () => api?.cancel());
 
-if (!api) showError('Tab import is not available in this build of Blanc.');
-else api.get().then(render).catch(() => showError('Blanc could not read this handoff.'));
+if (!api) showError('Tab import is not available in this build of Ember Browser.');
+else api.get().then(render).catch(() => showError('Ember Browser could not read this handoff.'));
