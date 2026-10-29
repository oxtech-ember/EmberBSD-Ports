Keep the saved SSL handle only when the SSL cleanup path uses it.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- pcap-rpcap.c.orig
+++ pcap-rpcap.c
@@ -108,7 +108,9 @@
  * pcap_remoteact_cleanup() for more details.
  */
 static PCAP_SOCKET sockmain;
+#ifdef HAVE_OPENSSL
 static SSL *ssl_main;
+#endif
 
 /*
  * Private data for capturing remotely using the rpcap protocol.
@@ -2645,8 +2647,10 @@
 		return NULL;
 	}
 
+#ifdef HAVE_OPENSSL
 	/* All good so far, save the ssl handler */
 	ssl_main = ssl;
+#endif
 
 	/*
 	 * Now it's time to start playing with the RPCAP protocol
