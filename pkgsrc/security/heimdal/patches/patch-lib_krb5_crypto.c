$NetBSD$

Use opaque OpenSSL contexts in the native NetBSD backend while preserving
keyed schedule state and explicit failure cleanup.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle corrections.

--- lib/krb5/crypto.c
+++ lib/krb5/crypto.c
@@ -156,6 +156,17 @@
 	return ret;
     }
     (*kt->schedule)(context, kt, key);
+#ifdef HEIMDAL_OPAQUE_EVP
+    if (kt->schedule == _krb5_evp_schedule) {
+        struct _krb5_evp_schedule *schedule = key->schedule->data;
+        if (schedule->error != 0) {
+            ret = schedule->error;
+            krb5_free_data(context, key->schedule);
+            key->schedule = NULL;
+            return ret;
+        }
+    }
+#endif
     return 0;
 }
 
