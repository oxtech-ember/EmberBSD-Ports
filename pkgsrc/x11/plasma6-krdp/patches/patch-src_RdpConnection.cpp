$NetBSD$

NetBSD pthread_setname_np takes a third argument.

--- src/RdpConnection.cpp.orig
+++ src/RdpConnection.cpp
@@ -515,7 +515,11 @@
 
     // Perform actual communication on a separate thread.
     d->thread = std::jthread(std::bind(&RdpConnection::run, this, std::placeholders::_1));
+#if defined(__NetBSD__)
+    pthread_setname_np(d->thread.native_handle(), "krdp_session", nullptr);
+#else
     pthread_setname_np(d->thread.native_handle(), "krdp_session");
+#endif
 }
 
 void RdpConnection::run(std::stop_token stopToken)
