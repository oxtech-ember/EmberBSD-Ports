$NetBSD$

Discover installed pkgsrc voice libraries, and actually read the environment.
Origin: EmberBSD (AI-assisted).

--- src/plugins/tts/flite/qtexttospeech_flite_processor.cpp.orig
+++ src/plugins/tts/flite/qtexttospeech_flite_processor.cpp
@@ -62,7 +62,7 @@
 
     // Read available libraries
     static const QStringList ldPaths = [] {
-        const QProcessEnvironment pe;
+        const QProcessEnvironment pe = QProcessEnvironment::systemEnvironment();
         QStringList ldPaths = pe.value(u"LD_LIBRARY_PATH"_s).split(u":"_s, Qt::SkipEmptyParts);
         if (ldPaths.isEmpty()) {
             ldPaths = QStringList{
@@ -95,6 +95,9 @@
                 u"/usr/lib/i386-linux-gnu"_s,
 #endif
 
+                // Package prefix supplied by the Ports recipe.
+                u"@PREFIX@/lib"_s,
+
                 // generic paths
                 u"/usr/lib"_s,
                 u"/usr/local/lib"_s,
