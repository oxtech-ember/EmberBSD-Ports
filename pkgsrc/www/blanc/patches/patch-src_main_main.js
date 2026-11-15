$NetBSD$

Ember Browser package identity, updater and isolated web application mode.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/main.js
+++ src/main/main.js
@@ -1,4 +1,13 @@
 const { app, BrowserWindow, View, WebContentsView, session, ipcMain, Menu, nativeTheme, nativeImage, dialog, shell, net, powerMonitor, webContents, clipboard, utilityProcess, systemPreferences, desktopCapturer, screen, globalShortcut } = require('electron');
+const { parseWebAppArgs, initializeProfile, sameWebApp, effectivePrivate, webAppMenuModel, fullPageLayout } = require('./webapp-mode');
+let webAppMode;
+let pendingWebAppLaunch = null;
+try { webAppMode = parseWebAppArgs(process.argv); }
+catch (error) { console.error('[webapp] invalid arguments:', error.message); app.exit(2); return; }
+if (webAppMode) {
+  initializeProfile(app, require('fs'), webAppMode);
+  app.commandLine.appendSwitch('class', `WebApp-${webAppMode.id}`);
+}
 // Playwright's loader forces --password-store=basic before loading this entry.
 // Sync acceptance uses a real, unlocked CI keyring: select it before ready,
 // after that loader, without relaxing safeStorage's plaintext-fallback guard.
@@ -154,7 +163,9 @@
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
@@ -1511,23 +1522,11 @@
 // browser processes writing one profile's LevelDB/extension state
 // SIGSEGVs both (observed 2026-07-04, identical CrBrowserMain crashes in
 // dev and installed builds within seconds of each other).
-if (!app.isPackaged) {
+if (!app.isPackaged && !webAppMode) {
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
@@ -1564,6 +1563,17 @@
   if (!acceptanceTestMode) enableTempSweep();
   diagnostics.start();
   app.on('second-instance', (_e, commandLine) => {
+    if (webAppMode) {
+      let incoming; try { incoming = parseWebAppArgs(commandLine); } catch { return; }
+      if (!sameWebApp(webAppMode, incoming)) return;
+      const runtime = resolveExternalRuntime();
+      if (!runtime.window || runtime.window.isDestroyed() || !runtime.chromeReady) {
+        pendingWebAppLaunch = incoming;
+      } else {
+        notifyWebAppSecondLaunch(runtime, incoming);
+      }
+      return;
+    }
     const runtime = resolveExternalRuntime();
     withWindowRuntime(runtime, () => {
       openExternalUrls(urlsFromArgv(commandLine));
@@ -3316,7 +3326,7 @@
  *  for a fresh profile while the test profile has completed first run. */
 let firstRunPendingForTest = false;
 function firstRunPending() {
-  return !settings.isFirstRunComplete() || firstRunPendingForTest;
+  return !webAppMode && (!settings.isFirstRunComplete() || firstRunPendingForTest);
 }
 
 /** Nothing is archived before this wall-clock time: launch, resume and a
@@ -3629,7 +3639,7 @@
 
 function currentChromeLayout(content = rt().window.getContentBounds()) {
   const { width, height } = content;
-  return calculateChromeLayout({
+  const layout = calculateChromeLayout({
     width,
     height,
     chromeHeight: stripCovered() ? islandAutoHideModule.coveredStripHeight(process.platform) : rt().chromeHeight,
@@ -3637,6 +3647,7 @@
     tabLayout,
     verticalTabsWidth: verticalTabsPreferredWidth,
   });
+  return webAppMode ? fullPageLayout(layout, width, height) : layout;
 }
 
 /* ---- Island proximity ---------------------------------------------------
@@ -4435,6 +4446,7 @@
  * floating Island: restack when one does. Cheap when the order is right.
  */
 function keepIslandFloatOnTop(runtime = rt()) {
+  if (webAppMode) return;
   const window = runtime.window;
   if (!runtime.islandFloat || !window || window.isDestroyed()) return;
   const children = window.contentView.children;
@@ -5133,7 +5145,7 @@
 
 function currentTabBounds(tab) {
   const layout = currentChromeLayout();
-  const split = splitGeometry(layout);
+  const split = webAppMode ? null : splitGeometry(layout);
   if (split) {
     const index = split.split.tabIds.indexOf(tab?.id);
     return index >= 0 ? split.panes[index].content : layout.pageBounds;
@@ -7224,6 +7236,7 @@
 }
 
 function broadcastTabs() {
+  if (webAppMode && rt().window && !rt().window.isDestroyed()) buildWebAppMenu(rt());
   blockingProviders?.refresh();
   for (const [id, popup] of ublockPopups) {
     if (popup.runtime.activeTabId !== popup.tabId || popup.runtime.window?.isDestroyed()) closeUblockPopup(id);
@@ -7272,11 +7285,11 @@
   const card = glanceTab ? glanceCardGeometry(layout) : null;
   const cardView = liveGlanceCardView();
   // Mid-slide (auto-hide), page panes move toward their final bounds.
-  const slide = rt().islandSlide;
+  const slide = webAppMode ? null : rt().islandSlide;
   const place = (bounds) => slide
     ? islandAutoHideModule.slidingBounds(bounds, { stripTop: layout.pageBounds.y, animatedTop: slide.top })
     : bounds;
-  const split = splitGeometry(layout);
+  const split = webAppMode ? null : splitGeometry(layout);
   if (split) {
     split.split.tabIds.forEach((id, index) => {
       const pane = tabs.get(id);
@@ -9413,6 +9426,7 @@
 });
 
 function createTab(url = newTabUrl(), { private: isPrivate = false, groupId = null, view = null, pinned = false, muted = false, restoreHistory = null, openerTabId = null, openedInBackground = false, asleep = false, title = null, favicon = null, customTitle = null, pinnedHomeUrl = null, lastViewedAt = null, adoptView = null, allowLocalFile = false, inheritsDocumentPolicy = false, httpReferrer = null, managedExtension = false } = {}) {
+  isPrivate = effectivePrivate(webAppMode, isPrivate);
   if (/^chrome-extension:/i.test(url) && (isPrivate || !managedExtension)) return null;
   // Official builds load a granted local HTML file; a DRM build keeps a
   // granted local-file record as an inert placeholder (src/main/inert-local-file.js).
@@ -11570,7 +11584,8 @@
     // killed the main process. closeTab (see its own `if (wc && ...)` guard)
     // already treats this as nullable; this path did not.
     const wc = liveContents(tab);
-    if (wc && lastMainFrameMethod.get(wc.id) !== 'POST') wc.reload();
+    // Cached subresources can bypass the updated blocking policy.
+    if (wc && lastMainFrameMethod.get(wc.id) !== 'POST') wc.reloadIgnoringCache();
   });
 }
 
@@ -12536,7 +12551,43 @@
   return withWindowRuntime(runtime, () => buildMenuForRuntime(runtime));
 }
 
+function buildWebAppMenu(runtime) {
+  const bound = fn => bindWindowRuntime(runtime, fn);
+  const active = () => tabs.get(runtime.activeTabId);
+  const rows = webAppMenuModel(runtime.tabOrder.map(id => {
+    const tab = tabs.get(id); return tab ? { id, title: tab.title, url: tab.url } : null;
+  }), runtime.activeTabId);
+  const template = [
+    { label: 'Navigation', submenu: [
+      { label: 'Back', accelerator: 'Alt+Left', click: bound(() => { const n = liveContents(active())?.navigationHistory; if (n?.canGoBack()) n.goBack(); }) },
+      { label: 'Forward', accelerator: 'Alt+Right', click: bound(() => { const n = liveContents(active())?.navigationHistory; if (n?.canGoForward()) n.goForward(); }) },
+      { label: 'Reload', accelerator: 'CmdOrCtrl+R', click: bound(() => liveContents(active())?.reload()) },
+      { label: 'Open address', accelerator: 'CmdOrCtrl+L', click: bound(() => focusAddressBar()) },
+      { label: 'Open in browser', click: bound(() => {
+        const url = liveContents(active())?.getURL() || '';
+        if (/^https?:\/\//i.test(url)) shell.openExternal(url).catch(error => console.error('[webapp] open in browser:', error.message));
+      }) },
+    ] },
+    { label: 'Tabs', submenu: [
+      { label: 'New tab', accelerator: 'CmdOrCtrl+T', click: bound(() => {
+        const id = createTab(webAppMode.url, { private: webAppMode.private });
+        if (id) setActiveTab(id, { focusContent: true });
+      }) },
+      { type: 'separator' },
+      ...rows.map(row => ({ label: row.label, type: 'checkbox', checked: row.checked,
+        click: bound(() => setActiveTab(row.id, { focusContent: true })) })),
+    ] },
+  ];
+  const menu = Menu.buildFromTemplate(template);
+  Menu.setApplicationMenu(menu);
+  if (runtime.window && !runtime.window.isDestroyed()) {
+    runtime.window.setAutoHideMenuBar(false);
+    runtime.window.setMenu(menu);
+  }
+}
+
 function buildMenuForRuntime(runtime) {
+  if (webAppMode) return buildWebAppMenu(runtime);
   const isMac = process.platform === 'darwin';
   // On Windows/Linux native menus a lone "&" marks the next char as an Alt
   // mnemonic and is swallowed; a literal ampersand must be doubled. macOS
@@ -13181,10 +13232,22 @@
   return withWindowRuntime(runtime, () => createMainWindowForRuntime(runtime, options));
 }
 
+function notifyWebAppSecondLaunch(runtime, incoming) {
+  if (!runtime.window || runtime.window.isDestroyed()) { pendingWebAppLaunch = incoming; return; }
+  bringExternalWindowToFront(app, runtime.window);
+  if (incoming.url !== webAppMode.url) {
+    void dialog.showMessageBox(runtime.window, {
+      type: 'info', buttons: ['OK'], defaultId: 0, noLink: true,
+      message: 'This web app is already running',
+      detail: 'Close it and open it again to use the updated address.',
+    });
+  }
+}
+
 function profileWindowTitle(profile) {
   return profile?.id === DEFAULT_PROFILE_ID
-    ? 'Blanc'
-    : `${profile?.name ?? mainI18n.t('profile.unnamed')} — Blanc`;
+    ? 'Ember Browser'
+    : `${profile?.name ?? mainI18n.t('profile.unnamed')} — Ember Browser`;
 }
 
 // `inactive`: shown without taking focus (a background routed link, #1199).
@@ -13214,10 +13277,10 @@
     // A mini window (#1138) isn't saved, so it keeps no placement either: it
     // opens small on the display under the pointer.
     ...(runtime.mini ? miniWindowPlacement() : windowStatePersistenceOptions(runtime.id)),
-    title: profileWindowTitle(localProfile),
+    title: webAppMode ? webAppMode.name : profileWindowTitle(localProfile),
     show: !inactive,
     backgroundColor: chromeBackgroundColor(),
-    frame: false,
+    frame: !!webAppMode,
     titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
     ...(windowIcon ? { icon: windowIcon } : {}),
     webPreferences: {
@@ -13236,7 +13299,7 @@
   // native window title bound to profile identity across loads and reloads.
   newWindow.on('page-title-updated', bindWindowRuntime(runtime, (event) => {
     event.preventDefault();
-    newWindow.setTitle(profileWindowTitle(localProfiles.getLocalProfile(runtime.profileId)));
+    newWindow.setTitle(webAppMode ? webAppMode.name : profileWindowTitle(localProfiles.getLocalProfile(runtime.profileId)));
   }));
   // The strip's own 68px band. Its document IS the window, so no offset.
   watchCursorFor(newWindow.webContents, { x: 0, y: 0 },
@@ -13456,6 +13519,10 @@
     runtime,
     () => {
       runtime.chromeReady = true;
+      if (webAppMode && pendingWebAppLaunch) {
+        const incoming = pendingWebAppLaunch; pendingWebAppLaunch = null;
+        notifyWebAppSecondLaunch(runtime, incoming);
+      }
       dockReopenLifecycle.onChromeReady();
       syncStripHidden(runtime);
     }
@@ -15608,7 +15675,7 @@
       // re-inks when the layout is changed from Settings or another window.
       layout: current.newtabLayout,
       privacy: {
-        required: !settings.isFirstRunComplete(),
+        required: !webAppMode && !settings.isFirstRunComplete(),
         searchSuggestions: current.searchSuggestions,
         usagePing: current.usagePing,
       },
@@ -16895,12 +16962,13 @@
   // broadcasts are temporarily prevented from overwriting this snapshot.
   await resumePendingProfileDeletions();
   recaseSavedGroupNamesOnce();
-  const { windows, activeWindowId, readOnly } = loadWorkspace(ensureSessionStore().data);
+  const { windows: storedWindows, activeWindowId, readOnly } = loadWorkspace(ensureSessionStore().data);
+  const windows = webAppMode ? [] : storedWindows;
   sessionReadOnly = readOnly;
   const pendingProfileIds = new Set(profileDeletions.pendingProfileDeletions());
   // Read the crash ledger once, before either recovery branch can resolve it.
   // A clean launch returns pinned tabs home; recovery keeps their last pages.
-  const cleanStart = !diagnostics.sessionRecoveryPending();
+  const cleanStart = !!webAppMode || !diagnostics.sessionRecoveryPending();
   const savedWindows = windows
     .filter((saved) => !pendingProfileIds.has(saved.profileId))
     .map((saved) => {
@@ -16994,7 +17062,7 @@
       runtime.groups = savedWorkspace ? saved.groups : [];
       runtime.closedSlot = savedWorkspace ? clampClosedSlot(saved.closedSlot, saved.groups.length) : 0;
       runtime.closedSlotIds = runtime.groups.map((group) => group.id);
-      startupTabIds.set(runtime.id, createTab(NEW_TAB_URL));
+      startupTabIds.set(runtime.id, createTab(NEW_TAB_URL, { private: !!webAppMode?.private }));
     });
     startupRuntimes.push(runtime);
     if (savedWorkspace) {
@@ -17039,7 +17107,7 @@
   if (recoveryRequired) {
     createStartupRuntime(recoveryHostWindow(), { savedWorkspace: false });
   } else {
-    for (const saved of orderedSavedWindows()) createStartupRuntime(saved);
+    for (const saved of orderedSavedWindows()) createStartupRuntime(saved, { savedWorkspace: !webAppMode });
   }
   focusedRuntime = recoveryRequired
     ? startupRuntimes[0]
@@ -17255,15 +17323,27 @@
 
     // Cold-start URL handoff waits until the blocker decision and session
     // restore are both complete.
-    openExternalUrls(urlsFromArgv(process.argv.slice(1)));
-    pendingTabHandoffUrls.push(...tabImportUrlsFromArgv(process.argv.slice(1)));
+    if (webAppMode) {
+      withWindowRuntime(focusedRuntime, () => {
+        const previous = startupTabIds.get(focusedRuntime.id);
+        const id = createTab(webAppMode.url, { private: webAppMode.private });
+        if (!id) throw new Error('cannot create webapp tab');
+        setActiveTab(id, { focusContent: true });
+        if (previous && previous !== id && tabs.has(previous)) closeTab(previous, { selectReplacement: false });
+      });
+    } else {
+      openExternalUrls(urlsFromArgv(process.argv.slice(1)));
+      pendingTabHandoffUrls.push(...tabImportUrlsFromArgv(process.argv.slice(1)));
+    }
     externalUrlsFlushable = true;
     withWindowRuntime(focusedRuntime, flushExternalUrls);
     tabHandoffsFlushable = true;
     withWindowRuntime(focusedRuntime, flushTabHandoffs);
     maybeSendLaunchPing();
-    scheduleDefaultBrowserReminder();
-    maybeOpenWhatsNew().catch(() => {});
+    if (!webAppMode) {
+      scheduleDefaultBrowserReminder();
+      maybeOpenWhatsNew().catch(() => {});
+    }
 
     // Patron subscription revalidation — off the critical path, after the
     // navigation gate is released and session restore is done. The model's
