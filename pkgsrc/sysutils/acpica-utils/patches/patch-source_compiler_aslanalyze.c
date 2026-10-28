Carry pkgsrc bounded diagnostics for the shared message buffer.

--- source/compiler/aslanalyze.c.orig
+++ source/compiler/aslanalyze.c
@@ -328,7 +328,7 @@
          */
         if (ThisNodeBtype != 0)
         {
-            sprintf (AslGbl_MsgBuffer,
+            snprintf (AslGbl_MsgBuffer, sizeof (AslGbl_MsgBuffer),
                 "Method returns [%s], %s operator requires [%s]",
                 AslGbl_StringBuffer, OpInfo->Name, AslGbl_StringBuffer2);
 
