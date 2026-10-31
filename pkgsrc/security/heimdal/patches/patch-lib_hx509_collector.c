$NetBSD$

Transfer caller-owned keys only after fallible collector setup succeeds.

--- lib/hx509/collector.c.orig
+++ lib/hx509/collector.c
@@ -140,9 +140,7 @@
 			       "AlgorithmIdentifier");
 	goto out;
     }
-    if (private_key) {
-	key->private_key = private_key;
-    } else {
+    if (private_key == NULL) {
 	ret = hx509_parse_private_key(context, alg,
 				       key_data->data, key_data->length,
 				       HX509_KEY_FORMAT_DER,
@@ -160,6 +158,9 @@
     } else
 	memset(&key->localKeyId, 0, sizeof(key->localKeyId));
 
+    /* Transfer caller ownership only after every fallible copy succeeds. */
+    if (private_key != NULL)
+        key->private_key = private_key;
     c->val.data[c->val.len] = key;
     c->val.len++;
 
