$NetBSD$

Adapt the KiCad IPC server to NNG 2. Pair every successful library initialization
with finalization and retain message ownership and orderly server shutdown.

--- libs/kinng/src/kinng.cpp.orig
+++ libs/kinng/src/kinng.cpp
@@ -20,7 +20,6 @@
 
 #include <kinng.h>
 #include <nng/nng.h>
-#include <nng/protocol/reqrep0/rep.h>
 #include <wx/log.h>
 
 
@@ -66,10 +65,10 @@
 
     {
         std::lock_guard<std::mutex> lock( m_mutex );
+        m_shutdown.store( true );
         m_replyReady.notify_all();
     }
 
-    m_shutdown.store( true );
     m_thread.join();
 }
 
@@ -90,6 +89,19 @@
 
     wxLogTrace( TraceNng, wxS( "KINNG_REQUEST_SERVER starting" ) );
 
+    retCode = nng_init( nullptr );
+
+    if( retCode != 0 )
+    {
+        wxLogTrace( TraceNng, wxString::Format( wxS( "nng_init failed: %d" ), retCode ) );
+        return;
+    }
+
+    struct NNG_LIFETIME
+    {
+        ~NNG_LIFETIME() { nng_fini(); }
+    } lifetime;
+
     retCode = nng_rep0_open( &socket );
 
     if( retCode != 0 )
@@ -106,43 +118,54 @@
         wxLogTrace( TraceNng,
                     wxString::Format( wxS( "Got error code %d from nng_listener_create!" ),
                                       retCode ) );
+        nng_socket_close( socket );
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
+        nng_socket_close( socket );
+        return;
+    }
 
     wxLogTrace( TraceNng, wxS( "KINNG_REQUEST_SERVER listener has started" ) );
 
     while( !m_shutdown.load() )
     {
-        char*    buf = nullptr;
-        size_t   sz;
-        uint64_t val;
+        nng_msg* msg = nullptr;
 
-        retCode = nng_recv( socket, &buf, &sz, NNG_FLAG_ALLOC );
+        retCode = nng_recvmsg( socket, &msg, 0 );
 
         if( retCode == NNG_ETIMEDOUT )
             continue;
 
         if( retCode != 0 )
         {
-            nng_free( buf, sz );
             wxLogTrace( TraceNng,
-                        wxString::Format( wxS( "Got error code %d from nngc_recv!" ), retCode ) );
+                        wxString::Format( wxS( "Got error code %d from nng_recvmsg!" ), retCode ) );
             break;
         }
 
-        m_sharedMessage.assign( buf, sz );
+        m_sharedMessage.assign( static_cast<const char*>( nng_msg_body( msg ) ), nng_msg_len( msg ) );
+        nng_msg_free( msg );
 
         if( m_callback )
             m_callback( &m_sharedMessage );
 
         std::unique_lock<std::mutex> lock( m_mutex );
-        m_replyReady.wait( lock, [&]() { return !m_pendingReply.empty(); } );
+        m_replyReady.wait( lock, [&]() { return m_shutdown.load() || !m_pendingReply.empty(); } );
 
-        retCode = nng_send( socket, const_cast<std::string::value_type*>( m_pendingReply.c_str() ),
+        if( m_shutdown.load() )
+            break;
+
+        retCode = nng_send( socket, m_pendingReply.data(),
                             m_pendingReply.length(), 0 );
 
         if( retCode != 0 )
@@ -156,5 +179,5 @@
 
     wxLogTrace( TraceNng, wxS( "KINNG_REQUEST_SERVER shutting down" ) );
 
-    nng_close( socket );
+    nng_socket_close( socket );
 }
