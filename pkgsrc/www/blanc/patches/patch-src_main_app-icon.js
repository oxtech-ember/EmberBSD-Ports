$NetBSD$

Use the independent Ember Browser icon. Origin: EmberBSD (AI-assisted).

--- src/main/app-icon.js
+++ src/main/app-icon.js
@@ -26,8 +26,8 @@
   platform = process.platform,
   projectRoot = path.join(__dirname, '../..'),
 }) {
-  if (platform !== 'win32' || app.isPackaged) return null;
-  return path.join(projectRoot, 'build/windows-icons/icon-sunrise.ico');
+  if (platform !== 'win32') return null;
+  return path.join(__dirname, '../renderer/pages/ember-browser.png');
 }
 
 /**
@@ -51,34 +51,10 @@
 }) {
   if (platform !== 'darwin' || !app.dock) return null;
 
-  // A deliberately explicit, unpackaged-only seam for reviewing candidate
-  // artwork in the real Dock. It never changes Settings or packaged assets.
-  if (!app.isPackaged && developmentPreviewPath) {
-    const previewPath = darkAppearance && developmentDarkPreviewPath
-      ? developmentDarkPreviewPath
-      : developmentPreviewPath;
-    const previewIcon = nativeImage.createFromPath(previewPath);
-    if (!previewIcon.isEmpty()) {
-      app.dock.setIcon(previewIcon);
-      return { source: 'development-preview', path: previewPath };
-    }
-  }
-
-  if (app.isPackaged && macOSMajorVersion(systemVersion) >= NATIVE_ICON_MIN_MACOS) {
-    const nativeName = nativeIconNameFor(appIcon);
-    const adaptiveIcon = nativeImage.createFromNamedImage(nativeName);
-    if (!adaptiveIcon.isEmpty()) {
-      app.dock.setIcon(adaptiveIcon);
-      return { source: 'native', nativeName };
-    }
-  }
-
-  const safeId = APP_ICON_ASSETS[appIcon] ? appIcon : 'sunrise';
-  const renderedId = safeId === 'sunrise' && darkAppearance ? 'sunrise-dark' : safeId;
-  const flatIcon = nativeImage.createFromPath(path.join(iconsDirectory, `icon-${renderedId}.png`));
+  const flatIcon = nativeImage.createFromPath(path.join(iconsDirectory, 'ember-browser.png'));
   if (flatIcon.isEmpty()) return null;
   app.dock.setIcon(flatIcon);
-  return { source: 'png', appIcon: renderedId };
+  return { source: 'png', appIcon: 'ember-browser' };
 }
 
 module.exports = {
