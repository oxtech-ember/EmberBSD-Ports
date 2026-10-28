EmberBSD local repair, AI-assisted; not submitted upstream.
Only iASL uses ANOBJ_IS_ALIAS. In the runtime the same flag bit marks
dynamically allocated method AML, which must reach normal teardown.

--- source/components/namespace/nsobject.c.orig
+++ source/components/namespace/nsobject.c
@@ -200,8 +200,11 @@
 
     /* Alias nodes point directly to other namespace nodes; skip teardown */
     if ((Node->Type == ACPI_TYPE_LOCAL_ALIAS) ||
-        (Node->Type == ACPI_TYPE_LOCAL_METHOD_ALIAS) ||
-        (Node->Flags & ANOBJ_IS_ALIAS))
+        (Node->Type == ACPI_TYPE_LOCAL_METHOD_ALIAS)
+#ifdef ACPI_ASL_COMPILER
+        || (Node->Flags & ANOBJ_IS_ALIAS)
+#endif
+        )
     {
         Node->Object = NULL;
         return_VOID;
