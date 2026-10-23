$NetBSD$

Do not dereference the XML reader when an input file cannot be opened.
The reader is allocated only after QFile::open succeeds.
Origin: EmberBSD (AI-assisted).

--- src/tools/qtwaylandscanner/qtwaylandscanner.cpp.orig
+++ src/tools/qtwaylandscanner/qtwaylandscanner.cpp
@@ -1310,7 +1310,7 @@ bool Scanner::process()
 
 void Scanner::printErrors()
 {
-    if (m_xml->hasError())
+    if (m_xml && m_xml->hasError())
         fprintf(stderr, "XML error: %s\nLine %lld, column %lld\n", m_xml->errorString().toLocal8Bit().constData(), m_xml->lineNumber(), m_xml->columnNumber());
 }
 
