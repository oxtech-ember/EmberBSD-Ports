$NetBSD$

Show the local EmberBSD update status and use one system action.

--- discover/qml/UpdatesPage.qml.orig
+++ discover/qml/UpdatesPage.qml
@@ -12,6 +12,9 @@
     id: page
 
     title: i18n("Updates")
+
+    readonly property var applicationBackend: Discover.ResourcesModel.currentApplicationBackend
+    readonly property bool emberSystem: applicationBackend?.displayName === "EmberBSD"
 
     property string footerLabel: ""
     property int footerProgress: 0
@@ -160,7 +163,7 @@
     readonly property alias hasErrors: updateAction.hasErrors
     Kirigami.Action {
         id: updateAction
-        text: page.unselected > 0 ? i18nc("@action:button as in, 'update the selected items' ", "Update Selected") : i18nc("@action:button as in, 'update all items'", "Update All")
+        text: page.emberSystem ? i18nc("@action:button", "Update system") : page.unselected > 0 ? i18nc("@action:button as in, 'update the selected items' ", "Update Selected") : i18nc("@action:button as in, 'update all items'", "Update All")
         visible: updateModel.toUpdateCount
         icon.name: "update-none"
 
@@ -178,15 +181,24 @@
 
         spacing: 0
 
+        QQC2.Label {
+            Layout.fillWidth: true
+            padding: Kirigami.Units.smallSpacing
+            visible: page.emberSystem
+            textFormat: Text.PlainText
+            wrapMode: Text.Wrap
+            text: page.emberSystem ? page.applicationBackend.emberUpdateStatus : ""
+        }
+
         DiscoverInlineMessage {
             Layout.fillWidth: true
-            inlineMessage: Discover.ResourcesModel.inlineMessage
+            inlineMessage: page.emberSystem ? null : Discover.ResourcesModel.inlineMessage
         }
 
         Kirigami.InlineMessage {
             Layout.fillWidth: true
             position: Kirigami.InlineMessage.Position.Header
-            visible: resourcesUpdatesModel.needsReboot && page.state !== "fetching" && page.state !== "reboot"
+            visible: !page.emberSystem && resourcesUpdatesModel.needsReboot && page.state !== "fetching" && page.state !== "reboot"
             text: i18nc("@info", "A pending update will be installed when restarting the system.")
             icon.name: "system-reboot-update"
         }
@@ -611,6 +623,7 @@
             : resourcesUpdatesModel.isFetching           ? "fetching"
             : updateModel.hasUpdates                     ? "has-updates"
             : resourcesUpdatesModel.needsReboot          ? "reboot"
+            : page.emberSystem                           ? "system-status"
             : secSinceUpdate < 0                         ? "unknown"
             : secSinceUpdate === 0                       ? "now-uptodate"
             : secSinceUpdate < 1000 * 60 * 60 * 24       ? "uptodate"
@@ -643,6 +656,11 @@
 
     states: [
         State {
+            name: "system-status"
+            PropertyChanges { page.actions: [refreshAction] }
+            PropertyChanges { statusLabel.visible: false }
+        },
+        State {
             name: "fetching"
             PropertyChanges { page.footerLabel: i18nc("@info", "Fetching updates…") }
             PropertyChanges { page.footerProgress: Discover.ResourcesModel.fetchingUpdatesProgress }
