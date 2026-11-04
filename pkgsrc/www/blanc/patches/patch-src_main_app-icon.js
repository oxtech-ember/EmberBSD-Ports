$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/app-icon.js
+++ src/main/app-icon.js
@@ -49,8 +49,8 @@
   platform = process.platform,
   projectRoot = path.join(__dirname, '../..'),
 }) {
-  if (platform !== 'win32' || app.isPackaged) return null;
-  return path.join(projectRoot, 'build/windows-icons/icon-sunrise.ico');
+  if (platform !== 'win32') return null;
+  return path.join(__dirname, '../renderer/pages/ember-browser.png');
 }
 
 /**
@@ -77,40 +77,10 @@
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
-    const nativeName = nativeTargetFor(appIcon, iconStyle);
-    // Clearing the custom image puts back the live bundle icon, which macOS
-    // keeps restyling for appearance and Icon & widget style. Loading the same
-    // stack by name would hand back a fixed bitmap of it instead.
-    if (nativeName === BUNDLE_APP_ICON_NAME) {
-      app.dock.setIcon(null);
-      return { source: 'bundle', nativeName };
-    }
-    const adaptiveIcon = nativeImage.createFromNamedImage(nativeName);
-    if (!adaptiveIcon.isEmpty()) {
-      app.dock.setIcon(adaptiveIcon);
-      return { source: 'native', nativeName };
-    }
-  }
-
-  const renderedId = flatIconIdFor(appIcon, darkAppearance);
-  const flatIcon = nativeImage.createFromPath(path.join(iconsDirectory, `icon-${renderedId}.png`));
+  const flatIcon = nativeImage.createFromPath(path.join(iconsDirectory, 'ember-browser.png'));
   if (flatIcon.isEmpty()) return null;
   app.dock.setIcon(flatIcon);
-  return { source: 'png', appIcon: renderedId };
+  return { source: 'png', appIcon: 'ember-browser' };
 }
 
 /**
@@ -144,15 +114,7 @@
   const targetFor = ({
     appIcon, developmentPreviewPath = null, developmentDarkPreviewPath = null, darkAppearance = false, iconStyle = null,
   }) => {
-    return {
-      preview: !app.isPackaged && developmentPreviewPath
-        ? (darkAppearance && developmentDarkPreviewPath ? developmentDarkPreviewPath : developmentPreviewPath)
-        : null,
-      native: app.isPackaged && macOSMajorVersion(systemVersion) >= NATIVE_ICON_MIN_MACOS
-        ? nativeTargetFor(appIcon, iconStyle)
-        : null,
-      png: flatIconIdFor(appIcon, darkAppearance),
-    };
+    return { preview: null, native: null, png: 'ember-browser' };
   };
   // A source earlier in applyDockAppIcon's order that failed before fails
   // again for the same target, so only the source that was shown is compared.
