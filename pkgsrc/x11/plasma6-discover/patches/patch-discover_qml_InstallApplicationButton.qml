$NetBSD$

Install an available catalog package. Removal and reinstall stay unavailable.

--- discover/qml/InstallApplicationButton.qml.orig
+++ discover/qml/InstallApplicationButton.qml
@@ -25,6 +25,12 @@
 
     readonly property Kirigami.Action action: Kirigami.Action {
         text: {
+            if (root.application.backend.displayName === "EmberBSD") {
+                if (root.application.state === Discover.AbstractResource.Upgradeable)
+                    return i18nc("@action:button", "Update stays unavailable until a verified helper exists")
+                if (!root.application.isInstalled)
+                    return i18nc("@action:button", "Install")
+            }
             if (!root.isStateAvailable) {
                 return i18nc("State being fetched", "Loading…")
             }
@@ -43,7 +49,7 @@
                 : Kirigami.Theme.backgroundColor
         }
         visible: !root.isActive && (!root.application.isInstalled || root.application.isRemovable)
-        enabled: !root.isActive && root.isStateAvailable
+        enabled: !root.isActive && root.isStateAvailable && (root.application.backend.displayName !== "EmberBSD" || !root.application.isInstalled)
         onTriggered: root.click()
     }
 
@@ -109,8 +115,8 @@
         QQC2.Button {
             id: installOrRemoveButton
 
-            visible: !root.application.isInstalled || root.application.isRemovable
-            enabled: root.application.state !== Discover.AbstractResource.Broken
+            visible: root.application.backend.displayName === "EmberBSD" ? (!root.application.isInstalled || root.application.state === Discover.AbstractResource.Upgradeable) : (!root.application.isInstalled || root.application.isRemovable)
+            enabled: (root.application.backend.displayName !== "EmberBSD" || !root.application.isInstalled) && root.application.state !== Discover.AbstractResource.Broken
             activeFocusOnTab: root.buttonActiveFocusOnTab
 
             display: invokeButton.visible ? QQC2.AbstractButton.IconOnly : root.installOrRemoveButtonDisplayStyle
