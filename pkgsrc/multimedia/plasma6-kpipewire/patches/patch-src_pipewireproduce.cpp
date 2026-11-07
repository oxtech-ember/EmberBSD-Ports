$NetBSD$

NetBSD pthread_setname_np takes a printf format and an argument.

--- src/pipewireproduce.cpp.orig
+++ src/pipewireproduce.cpp
@@ -297,6 +297,8 @@
     });
 #if defined(Q_OS_OPENBSD)
     pthread_set_name_np(m_passthroughThread.native_handle(), "PipeWireProduce::passthrough");
+#elif defined(Q_OS_NETBSD)
+    pthread_setname_np(m_passthroughThread.native_handle(), "%s", const_cast<char *>("PipeWireProduce::passthrough"));
 #else
     pthread_setname_np(m_passthroughThread.native_handle(), "PipeWireProduce::passthrough");
 #endif
@@ -331,6 +333,8 @@
     });
 #if defined(Q_OS_OPENBSD)
     pthread_set_name_np(m_outputThread.native_handle(), "PipeWireProduce::output");
+#elif defined(Q_OS_NETBSD)
+    pthread_setname_np(m_outputThread.native_handle(), "%s", const_cast<char *>("PipeWireProduce::output"));
 #else
     pthread_setname_np(m_outputThread.native_handle(), "PipeWireProduce::output");
 #endif
