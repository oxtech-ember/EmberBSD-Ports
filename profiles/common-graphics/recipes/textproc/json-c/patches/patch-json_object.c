$NetBSD$

Origin: EmberBSD (AI-assisted).
Release a copied key when hash-table insertion fails. The caller still owns
the value on this failure path. A constant key must never be released.

--- json_object.c.orig
+++ json_object.c
@@ -723,11 +723,17 @@
 
 	if (!existing_entry)
 	{
+		char *const key_copy =
+		    (opts & JSON_C_OBJECT_ADD_CONSTANT_KEY) ? NULL : strdup(key);
 		const void *const k =
-		    (opts & JSON_C_OBJECT_ADD_CONSTANT_KEY) ? (const void *)key : strdup(key);
+		    (opts & JSON_C_OBJECT_ADD_CONSTANT_KEY) ? (const void *)key : key_copy;
+		int rc;
 		if (k == NULL)
 			return -1;
-		return lh_table_insert_w_hash(JC_OBJECT(jso)->c_object, k, val, hash, opts);
+		rc = lh_table_insert_w_hash(JC_OBJECT(jso)->c_object, k, val, hash, opts);
+		if (rc != 0)
+			free(key_copy);
+		return rc;
 	}
 	existing_value = (json_object *)lh_entry_v(existing_entry);
 	if (existing_value)
