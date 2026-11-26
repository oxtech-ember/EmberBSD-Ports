$NetBSD$

Install an available catalog package. System updates use the Updates page.

--- discover/qml/InstallApplicationButton.qml.orig
+++ discover/qml/InstallApplicationButton.qml
@@ -23,8 +23,15 @@
         id: listener
     }
 
+    readonly property bool emberRestartRequired: root.application.backend.displayName === "EmberBSD" && root.application.backend.emberRestartRequired
+    readonly property bool emberStaged: emberRestartRequired && root.application.backend.emberStagedPackages.includes(root.application.packageName + "-" + root.application.availableVersion)
+
     readonly property Kirigami.Action action: Kirigami.Action {
         text: {
+            if (!root.application.isInstalled && root.emberRestartRequired)
+                return root.emberStaged ? i18nc("@action:button", "Installing after restart") : i18nc("@action:button", "Restart before installing")
+            if (root.application.backend.displayName === "EmberBSD" && !root.application.isInstalled)
+                return i18nc("@action:button", "Install")
             if (!root.isStateAvailable) {
                 return i18nc("State being fetched", "Loading…")
             }
@@ -43,7 +50,7 @@
                 : Kirigami.Theme.backgroundColor
         }
         visible: !root.isActive && (!root.application.isInstalled || root.application.isRemovable)
-        enabled: !root.isActive && root.isStateAvailable
+        enabled: !root.isActive && root.isStateAvailable && !root.emberRestartRequired && (root.application.backend.displayName !== "EmberBSD" || !root.application.isInstalled)
         onTriggered: root.click()
     }
 
@@ -110,7 +117,7 @@
             id: installOrRemoveButton
 
             visible: !root.application.isInstalled || root.application.isRemovable
-            enabled: root.application.state !== Discover.AbstractResource.Broken
+            enabled: !root.emberRestartRequired && (root.application.backend.displayName !== "EmberBSD" || !root.application.isInstalled) && root.application.state !== Discover.AbstractResource.Broken
             activeFocusOnTab: root.buttonActiveFocusOnTab
 
             display: invokeButton.visible ? QQC2.AbstractButton.IconOnly : root.installOrRemoveButtonDisplayStyle
