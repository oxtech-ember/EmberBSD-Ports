$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Resolve data and tools within the selected installation during relocation.

--- config-kdoctools.h.cmake.orig
+++ config-kdoctools.h.cmake
@@ -3,3 +3,8 @@
 #define DOCBOOK_XML_CURRDTD "@DocBookXML4_DTD_DIR@"
 
 #define KDOCTOOLS_INSTALL_DATADIR_KF "${CMAKE_INSTALL_PREFIX}/${KDE_INSTALL_DATADIR_KF}"
+
+#define KDOCTOOLS_BINDIR_TO_DATADIR_KF "${KDOCTOOLS_BINDIR_TO_DATADIR_KF}"
+
+#cmakedefine01 RELOCATABLE_DOCBOOK_FILES
+#define KDOCTOOLS_LIBDIR_TO_DATADIR_KF "${KDOCTOOLS_LIBDIR_TO_DATADIR_KF}"
