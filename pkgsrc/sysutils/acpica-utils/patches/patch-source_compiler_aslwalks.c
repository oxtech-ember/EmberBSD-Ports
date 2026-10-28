Carry pkgsrc bounded diagnostics for the shared message buffer.

--- source/compiler/aslwalks.c.orig
+++ source/compiler/aslwalks.c
@@ -502,7 +502,7 @@
                 AnFormatBtype (AslGbl_StringBuffer, ThisNodeBtype);
                 AnFormatBtype (AslGbl_StringBuffer2, RequiredBtypes);
 
-                sprintf (AslGbl_MsgBuffer, "[%s] found, %s operator requires [%s]",
+                snprintf (AslGbl_MsgBuffer, sizeof (AslGbl_MsgBuffer), "[%s] found, %s operator requires [%s]",
                     AslGbl_StringBuffer, OpInfo->Name, AslGbl_StringBuffer2);
 
                 AslError (ASL_ERROR, ASL_MSG_INVALID_TYPE,
