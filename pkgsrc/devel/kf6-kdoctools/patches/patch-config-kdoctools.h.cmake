$NetBSD$

Origin: EmberBSD (AI-assisted), not submitted upstream.
Find the KDocTools data relative to the running executable as well,
so tools from a relocated or selected prefix find their own data.

--- config-kdoctools.h.cmake.orig
+++ config-kdoctools.h.cmake
@@ -3,3 +3,5 @@
 #define DOCBOOK_XML_CURRDTD "@DocBookXML4_DTD_DIR@"
 
 #define KDOCTOOLS_INSTALL_DATADIR_KF "${CMAKE_INSTALL_PREFIX}/${KDE_INSTALL_DATADIR_KF}"
+
+#define KDOCTOOLS_BINDIR_TO_DATADIR_KF "${KDOCTOOLS_BINDIR_TO_DATADIR_KF}"
