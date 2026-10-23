Keep the structured URI list instead of overwriting it with raw MIME bytes.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- lib/mousehelper.cpp.orig
+++ lib/mousehelper.cpp
@@ -43,6 +43,7 @@
     if (it != formats.cend()) {
         const QList<QUrl> urls = data->urls();
         dataMap.insert(*it, QVariantList(urls.cbegin(), urls.cend()));
+        formats.erase(it);
     }
 
     it = std::find_if(formats.cbegin(), formats.cend(), [](const QString &format) {
