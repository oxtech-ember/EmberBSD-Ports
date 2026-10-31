$NetBSD$

Backport Qt security fix CVE-2026-105924.
From Thiago Macieira, Qt commit a2cd9d2a70575c37153d43e9c5396a9144af1923.
https://download.qt.io/official_releases/qt/6.12/CVE-2026-105924-qtbase-6.12.diff

diff --git a/src/corelib/serialization/qjsoncbor.cpp b/src/corelib/serialization/qjsoncbor.cpp
index cbee0a4..fd641a3 100644
--- src/corelib/serialization/qjsoncbor.cpp
+++ src/corelib/serialization/qjsoncbor.cpp
@@ -174,15 +174,21 @@
     qint64 tag = d->elements.at(0).value;
 
     switch (tag) {
-    case qint64(QCborKnownTags::Url):
+    case qint64(QCborKnownTags::Url): {
 #ifdef QT_BOOTSTRAPPED
         break;
 #else
         // use the fully-encoded URL form
-        if (d->elements.at(1).type == QCborValue::String)
-            return QUrl::fromEncoded(d->byteData(1)->asByteArrayView()).toString(QUrl::FullyEncoded);
+        Element e = d->elements.at(1);
+        const ByteData *bd = d->byteData(e);
+        if (e.type == QCborValue::String) {
+            if (!bd)
+                return QString();
+            return QUrl::fromEncoded(bd->asByteArrayView()).toString(QUrl::FullyEncoded);
+        }
         Q_FALLTHROUGH();
 #endif
+    }
 
     case qint64(QCborKnownTags::DateTimeString):
     case qint64(QCborKnownTags::ExpectedBase64url):
