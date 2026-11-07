$NetBSD$

Do not wait for the KDE featured URL. List verified desktop applications.

--- discover/FeaturedModel.cpp.orig
+++ discover/FeaturedModel.cpp
@@ -17,6 +17,8 @@
 #include <QStandardPaths>
 #include <QtGlobal>
 
+#include <Category/CategoryModel.h>
+#include <resources/AbstractResourcesBackend.h>
 #include <resources/ResourcesModel.h>
 #include <utils.h>
 
@@ -41,6 +43,10 @@
 
 FeaturedModel::FeaturedModel()
 {
+    if (auto *backend = currentApplicationBackend(); backend && backend->displayName() == u"EmberBSD"_s) {
+        refreshEmberBSD();
+        return;
+    }
     const QString dir = QStandardPaths::writableLocation(QStandardPaths::CacheLocation);
     QDir().mkpath(dir);
 
@@ -75,6 +81,10 @@
 
 void FeaturedModel::refresh()
 {
+    if (auto *backend = currentApplicationBackend(); backend && backend->displayName() == u"EmberBSD"_s) {
+        refreshEmberBSD();
+        return;
+    }
     // usually only useful if launching just fwupd or kns backends
     if (!currentApplicationBackend())
         return;
@@ -101,4 +111,21 @@
     setUris(uris);
 }
 
+void FeaturedModel::refreshEmberBSD()
+{
+    auto *backend = currentApplicationBackend();
+    if (!backend)
+        return;
+
+    // The home page waits on this model. Use the signed catalog's verified
+    // desktop applications instead of the KDE featured URL list.
+    acquireFetching(true);
+    AbstractResourcesBackend::Filters filter;
+    const auto category = CategoryModel::global()->findCategoryByName(QStringLiteral("All Applications"));
+    if (category)
+        filter.category = category;
+    auto *stream = new AggregatedResultsStream({backend->search(filter)});
+    connect(stream, &AggregatedResultsStream::finished, this, &AbstractAppsModel::setResources);
+}
+
 #include "moc_FeaturedModel.cpp"
