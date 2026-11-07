$NetBSD$

Keep install and remove disabled for the read-only catalog.

--- discover/qml/InstallApplicationButton.qml.orig
+++ discover/qml/InstallApplicationButton.qml
@@ -25,6 +25,9 @@
 
     readonly property Kirigami.Action action: Kirigami.Action {
         text: {
+            if (root.application.backend.displayName === "EmberBSD") {
+                return i18nc("@action:button", "Install and remove stay unavailable until a verified helper exists")
+            }
             if (!root.isStateAvailable) {
                 return i18nc("State being fetched", "Loading…")
             }
@@ -43,7 +46,7 @@
                 : Kirigami.Theme.backgroundColor
         }
         visible: !root.isActive && (!root.application.isInstalled || root.application.isRemovable)
-        enabled: !root.isActive && root.isStateAvailable
+        enabled: !root.isActive && root.isStateAvailable && root.application.backend.displayName !== "EmberBSD"
         onTriggered: root.click()
     }
 
@@ -109,8 +112,8 @@
         QQC2.Button {
             id: installOrRemoveButton
 
-            visible: !root.application.isInstalled || root.application.isRemovable
-            enabled: root.application.state !== Discover.AbstractResource.Broken
+            visible: root.application.backend.displayName === "EmberBSD" || !root.application.isInstalled || root.application.isRemovable
+            enabled: root.application.backend.displayName !== "EmberBSD" && root.application.state !== Discover.AbstractResource.Broken
             activeFocusOnTab: root.buttonActiveFocusOnTab
 
             display: invokeButton.visible ? QQC2.AbstractButton.IconOnly : root.installOrRemoveButtonDisplayStyle
