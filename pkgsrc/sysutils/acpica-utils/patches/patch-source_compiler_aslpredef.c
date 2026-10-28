Carry pkgsrc bounded diagnostics for the shared message buffer.

--- source/compiler/aslpredef.c.orig
+++ source/compiler/aslpredef.c
@@ -133,7 +133,7 @@
             AcpiUtGetExpectedReturnTypes (AslGbl_StringBuffer,
                 ThisName->Info.ExpectedBtypes);
 
-            sprintf (AslGbl_MsgBuffer, "%s required for %4.4s",
+            snprintf (AslGbl_MsgBuffer, sizeof (AslGbl_MsgBuffer), "%s required for %4.4s",
                 AslGbl_StringBuffer, ThisName->Info.Name);
 
             AslError (ASL_WARNING, ASL_MSG_RESERVED_RETURN_VALUE, Op,
