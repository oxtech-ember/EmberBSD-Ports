$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/renderer/pages/tab-import-open-tabs.js
+++ src/renderer/pages/tab-import-open-tabs.js
@@ -154,7 +154,7 @@
 }
 
 function tabImportApplyLabel({ tabs }) {
-  return `Open ${tabs} ${tabs === 1 ? 'tab' : 'tabs'} in Blanc`;
+  return `Open ${tabs} ${tabs === 1 ? 'tab' : 'tabs'} in Ember Browser`;
 }
 
 function tabImportApplyRequest(reviewProposal = proposal, currentGeneration = generation) {
@@ -373,7 +373,7 @@
     sourceBrowserGroups = groupedSources(await api.sources());
     if (!sourceBrowserGroups.length) {
       const names = new Intl.ListFormat('en', { style: 'long', type: 'conjunction' }).format(SUPPORTED_BROWSER_NAMES);
-      loading.textContent = `Blanc can bring open tabs from ${names}, but none of them has a profile on this device. `
+      loading.textContent = `Ember Browser can bring open tabs from ${names}, but none of them has a profile on this device. `
         + 'To bring bookmarks from another browser, export them to an HTML file, then use “Import HTML…” in Favorites.';
       return;
     }
@@ -399,7 +399,7 @@
   title.textContent = `Finish saving tabs in ${browserName}`;
   const count = Number(result.recoverableTabCount) || 0;
   const copy = document.createElement('p');
-  copy.textContent = `Blanc found a saved, restorable session${count ? ` with ${count} ${count === 1 ? 'tab' : 'tabs'}` : ''}. Quit ${browserName} normally so it can finish saving the latest session. Blanc only reads it and never removes tabs from ${browserName}.`;
+  copy.textContent = `Ember Browser found a saved, restorable session${count ? ` with ${count} ${count === 1 ? 'tab' : 'tabs'}` : ''}. Quit ${browserName} normally so it can finish saving the latest session. Ember Browser only reads it and never removes tabs from ${browserName}.`;
   const note = document.createElement('p');
   note.className = 'section-hint';
   note.textContent = `Whether those tabs reopen automatically in ${browserName} depends on its startup setting.`;
@@ -417,17 +417,17 @@
 
 function sourceError(result, label, afterQuit, browserName = label) {
   if (afterQuit && ['source-locked', 'source-saving', 'incomplete-session', 'missing-session-marker'].includes(result.error)) {
-    return `The latest ${label} session is not safely readable. Reopen ${browserName}; Blanc will not use an older snapshot.`;
+    return `The latest ${label} session is not safely readable. Reopen ${browserName}; Ember Browser will not use an older snapshot.`;
   }
   return ({
     'source-unavailable': 'That browser profile is no longer available.',
-    permission: 'macOS blocked this profile. Grant Blanc Full Disk Access, then try again.',
+    permission: 'macOS blocked this profile. Grant Ember Browser Full Disk Access, then try again.',
     'session-too-large': 'That saved session is too large to import safely.',
     'too-many-candidates': 'This profile has more than 500 open tabs. Nothing was changed.',
-    'encrypted-session': `${label} uses an encrypted session format Blanc does not access.`,
+    'encrypted-session': `${label} uses an encrypted session format Ember Browser does not access.`,
     empty: `No restorable open tabs were found in ${label}.`,
-    unreadable: `Blanc couldn’t read the saved ${label} session.`,
-  })[result.error] ?? `Blanc couldn’t read open tabs from ${label}.`;
+    unreadable: `Ember Browser couldn’t read the saved ${label} session.`,
+  })[result.error] ?? `Ember Browser couldn’t read open tabs from ${label}.`;
 }
 
 async function openSource(id, label, { afterQuit = false, browserName = label } = {}) {
@@ -456,7 +456,7 @@
     setStep('tabs');
     setStatus();
   } catch {
-    setStatus(`Blanc couldn’t read open tabs from ${label}.`);
+    setStatus(`Ember Browser couldn’t read open tabs from ${label}.`);
   } finally {
     const waitingForQuit = !sourceRecoveryEl.hidden;
     for (const button of sourceListEl.querySelectorAll('button')) {
@@ -874,7 +874,7 @@
     if (result.retryable && result.phase === 'activation') {
       pendingApplyPhase = 'activation';
       generation = result.generation ?? generation;
-      setStatus('Your tabs are ready, but Blanc could not focus the first one.');
+      setStatus('Your tabs are ready, but Ember Browser could not focus the first one.');
       applyBtn.textContent = 'Focus the first imported tab';
       applyBtn.disabled = false;
       return;
@@ -886,10 +886,10 @@
       setStatus();
       return;
     }
-    setStatus("Blanc couldn't open these tabs. Nothing was partially imported.");
+    setStatus("Ember Browser couldn't open these tabs. Nothing was partially imported.");
     applyBtn.disabled = false;
   } catch {
-    setStatus("Blanc couldn't open these tabs. Nothing was partially imported.");
+    setStatus("Ember Browser couldn't open these tabs. Nothing was partially imported.");
     applyBtn.disabled = false;
   }
 }
