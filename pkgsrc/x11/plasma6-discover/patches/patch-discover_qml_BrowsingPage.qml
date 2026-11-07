$NetBSD$

Name the home cards as desktop applications for this backend.

--- discover/qml/BrowsingPage.qml.orig
+++ discover/qml/BrowsingPage.qml
@@ -138,7 +138,9 @@
             Layout.bottomMargin: -(apps.rowSpacing / 2)
             Layout.columnSpan: apps.columns
             Layout.fillWidth: true
-            text: i18nc("@title:group", "Editor’s Choice")
+            text: (featuredModel.currentApplicationBackend && featuredModel.currentApplicationBackend.displayName === "EmberBSD")
+                ? i18nc("@title:group", "Desktop applications")
+                : i18nc("@title:group", "Editor’s Choice")
             wrapMode: Text.Wrap
             visible: featuredRep.count > 0 && !featuredModel.isFetching
         }
