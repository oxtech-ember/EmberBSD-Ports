$NetBSD$

Do not treat an unknown reachability report as offline.

Qt's glib plugin rejects GNetworkMonitorBase, so on this system
reachability stays Unknown for the whole run. The catalog load is
separate and must still report its own transport and signature errors.

--- discover/qml/DiscoverWindow.qml.orig
+++ discover/qml/DiscoverWindow.qml
@@ -46,15 +46,32 @@
         active: window.visible
     }
 
+    function knownOffline() {
+        const reachability = NetworkInformation.reachability
+        return reachability === NetworkInformation.Reachability.Disconnected
+            || reachability === NetworkInformation.Reachability.Local
+            || reachability === NetworkInformation.Reachability.Site
+    }
+
     Component.onCompleted: {
         if (app.isRoot) {
             messagesSheet.addMessage(i18n("Running as <em>root</em> is discouraged and unnecessary."));
         }
 
-        if (NetworkInformation.reachability !== NetworkInformation.Reachability.Online) {
+        if (knownOffline()) {
             connectionDialog.open();
         }
     }
+
+    Connections {
+        target: NetworkInformation
+        function onReachabilityChanged() {
+            if (window.knownOffline())
+                connectionDialog.open()
+            else if (NetworkInformation.reachability === NetworkInformation.Reachability.Online)
+                connectionDialog.close()
+        }
+    }
 
     // This property is queried from C++, do not remove it
     readonly property string describeSources: feedbackLoader.item?.describeDataSources ?? ""
