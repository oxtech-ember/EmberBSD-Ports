$NetBSD$

Origin: EmberBSD (AI-assisted). Assert the native Qt/kqueue default while retaining the
full upstream file-event regression suite.

--- autotests/kdirwatch_unittest.cpp.orig
+++ autotests/kdirwatch_unittest.cpp
@@ -51,6 +51,11 @@
 private Q_SLOTS: // test methods
     void initTestCase()
     {
+#if defined(Q_OS_NETBSD) && HAVE_QFILESYSTEMWATCHER
+        if (QByteArray(KDIRWATCH_TEST_METHOD) == "default") {
+            QCOMPARE(s_staticObject()->m_dirWatch.internalMethod(), KDirWatch::QFSWatch);
+        }
+#endif
         QFileInfo pathInfo(m_path);
         QVERIFY(pathInfo.isDir() && pathInfo.isWritable());
 
