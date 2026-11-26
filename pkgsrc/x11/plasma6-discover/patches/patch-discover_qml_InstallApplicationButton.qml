$NetBSD$

Install an available catalog package. System updates use the Updates page.

--- discover/qml/InstallApplicationButton.qml.orig
+++ discover/qml/InstallApplicationButton.qml
@@ -25,6 +25,8 @@
 
     readonly property Kirigami.Action action: Kirigami.Action {
         text: {
+            if (root.application.backend.displayName === "EmberBSD" && !root.application.isInstalled)
+                return i18nc("@action:button", "Install")
             if (!root.isStateAvailable) {
                 return i18nc("State being fetched", "Loading…")
             }
@@ -43,7 +45,7 @@
                 : Kirigami.Theme.backgroundColor
         }
         visible: !root.isActive && (!root.application.isInstalled || root.application.isRemovable)
-        enabled: !root.isActive && root.isStateAvailable
+        enabled: !root.isActive && root.isStateAvailable && (root.application.backend.displayName !== "EmberBSD" || !root.application.isInstalled)
         onTriggered: root.click()
     }
 
@@ -110,7 +112,7 @@
             id: installOrRemoveButton
 
             visible: !root.application.isInstalled || root.application.isRemovable
-            enabled: root.application.state !== Discover.AbstractResource.Broken
+            enabled: (root.application.backend.displayName !== "EmberBSD" || !root.application.isInstalled) && root.application.state !== Discover.AbstractResource.Broken
             activeFocusOnTab: root.buttonActiveFocusOnTab
 
             display: invokeButton.visible ? QQC2.AbstractButton.IconOnly : root.installOrRemoveButtonDisplayStyle
