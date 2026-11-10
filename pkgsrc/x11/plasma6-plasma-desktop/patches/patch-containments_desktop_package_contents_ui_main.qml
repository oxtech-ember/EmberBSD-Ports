$NetBSD$

Avoid Wayland DropJob popup when dropping .desktop launchers on the desktop.
Kickoff closes on drop; an xdg_popup without a stable parent can kill plasmashell
(KDE#488515 class). Link application shortcuts without the Copy/Move/Link menu.
Origin: EmberBSD (AI-assisted).

--- containments/desktop/package/contents/ui/main.qml.orig
+++ containments/desktop/package/contents/ui/main.qml
@@ -254,6 +254,25 @@
         onDrop: event => {
             if (root.isFolder && FolderTools.isFileDrag(event)) {
                 handleDragEnd(folderViewLayer.view);
+                // EmberBSD: Kickoff→desktop DropJob popup can kill plasmashell on Wayland
+                // when the launcher window closes (xdg_popup parent; KDE#488515 class).
+                // Link .desktop launchers without showing the Copy/Move/Link menu.
+                const urls = event.mimeData.urls;
+                let allDesktopLaunchers = urls && urls.length > 0;
+                for (let i = 0; i < urls.length; ++i) {
+                    const path = urls[i].toString();
+                    if (!path.endsWith(".desktop")) {
+                        allDesktopLaunchers = false;
+                        break;
+                    }
+                }
+                if (allDesktopLaunchers) {
+                    for (let i = 0; i < urls.length; ++i) {
+                        folderViewLayer.view.linkHere(urls[i]);
+                    }
+                    event.accept(event.proposedAction);
+                    return;
+                }
                 folderViewLayer.view.drop(root, event, mapToItem(folderViewLayer.view, event.x, event.y));
             } else if (root.isContainment) {
                 root.processMimeData(event.mimeData,
