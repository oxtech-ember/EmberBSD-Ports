$NetBSD$

# Origin: EmberBSD (AI-assisted). Fix request-buffer ownership and server shutdown.
# Source: KiCad 10.0.7, GPL-3.0-or-later; retain the upstream source notices.
--- libs/kinng/src/kinng.cpp.orig
+++ libs/kinng/src/kinng.cpp
@@ -66,10 +66,10 @@
 
     {
         std::lock_guard<std::mutex> lock( m_mutex );
+        m_shutdown.store( true );
         m_replyReady.notify_all();
     }
 
-    m_shutdown.store( true );
     m_thread.join();
 }
 
@@ -106,20 +106,29 @@
         wxLogTrace( TraceNng,
                     wxString::Format( wxS( "Got error code %d from nng_listener_create!" ),
                                       retCode ) );
+        nng_close( socket );
         return;
     }
 
     nng_socket_set_ms( socket, NNG_OPT_RECVTIMEO, 500 );
 
-    nng_listener_start( listener, 0 );
+    retCode = nng_listener_start( listener, 0 );
+
+    if( retCode != 0 )
+    {
+        wxLogTrace( TraceNng,
+                    wxString::Format( wxS( "Got error code %d from nng_listener_start!" ),
+                                      retCode ) );
+        nng_close( socket );
+        return;
+    }
 
     wxLogTrace( TraceNng, wxS( "KINNG_REQUEST_SERVER listener has started" ) );
 
     while( !m_shutdown.load() )
     {
         char*    buf = nullptr;
-        size_t   sz;
-        uint64_t val;
+        size_t   sz = 0;
 
         retCode = nng_recv( socket, &buf, &sz, NNG_FLAG_ALLOC );
 
@@ -128,19 +137,22 @@
 
         if( retCode != 0 )
         {
-            nng_free( buf, sz );
             wxLogTrace( TraceNng,
                         wxString::Format( wxS( "Got error code %d from nngc_recv!" ), retCode ) );
             break;
         }
 
         m_sharedMessage.assign( buf, sz );
+        nng_free( buf, sz );
 
         if( m_callback )
             m_callback( &m_sharedMessage );
 
         std::unique_lock<std::mutex> lock( m_mutex );
-        m_replyReady.wait( lock, [&]() { return !m_pendingReply.empty(); } );
+        m_replyReady.wait( lock, [&]() { return m_shutdown.load() || !m_pendingReply.empty(); } );
+
+        if( m_shutdown.load() )
+            break;
 
         retCode = nng_send( socket, const_cast<std::string::value_type*>( m_pendingReply.c_str() ),
                             m_pendingReply.length(), 0 );
