# Origin: EmberBSD (AI-assisted).
Preserve the OS rlog -c interface and optional output convention.
Use equivalent string indexing for Clang diagnostics.

--- src/rlog.c.orig
+++ src/rlog.c
@@ -33,6 +33,8 @@
 #include "b-fb.h"
 #include "b-fro.h"
 
+static bool show_commitid;
+
 static char const ks_delims[] = ", \t\n;";
 
 struct revrange
@@ -187,11 +189,16 @@
            node->num,
            pre5 ? "        " : "");
   if (node->lockedby)
-    aprintf (out, pre5 + "\tlocked by: %s;", node->lockedby);
+    aprintf (out, &"\tlocked by: %s;"[pre5], node->lockedby);
 
   aprintf (out, "\ndate: %s;  author: %s;  state: %s;",
            date2str (node->date, datebuf), node->author, node->state);
 
+#ifdef RCS_RLOG_EXPLICIT_COMMITID
+  if (show_commitid && node->commitid)
+    aprintf (out, "  commitid: %s;", node->commitid);
+#endif
+
   if (editscript && editscript != REPO (tip))
     {
       bool trunk = node != editscript;
@@ -214,10 +221,12 @@
         }
     }
 
-  if (node->commitid)
+#ifndef RCS_RLOG_EXPLICIT_COMMITID
+  if (show_commitid && node->commitid)
     aprintf (out, "%s commitid: %s",
              editscript ? ";" : "",
              node->commitid);
+#endif
 
   newline (out);
   if ((log = node->log)
@@ -733,6 +742,11 @@
   CHECK_HV (cmd);
   gnurcs_init (&program);
 
+#ifdef RCS_RLOG_EXPLICIT_COMMITID
+  show_commitid = false;
+#else
+  show_commitid = true;
+#endif
   descflag = selectflag = shownames = true;
   onlylockflag = onlyRCSflag = false;
   out = stdout;
@@ -744,6 +758,10 @@
       switch (*a++)
         {
 
+        case 'c':
+          show_commitid = true;
+          break;
+
         case 'L':
           onlylockflag = true;
           break;
@@ -903,7 +921,7 @@
                  strictly_locking ? " strict" : "");
         format_locks (out, symbolFormat);
         if (strictly_locking && pre5)
-          aputs ("  ;  strict" + (locks ? 3 : 0), out);
+          aputs (&"  ;  strict"[locks ? 3 : 0], out);
 
         /* Print access list.  */
         aputs (accessListString, out);
@@ -983,6 +1001,7 @@
 /*:help
 [options] file ...
 Options:
+  -c            Include CVS commit identifiers, when available.
   -L            Ignore RCS files with no locks set.
   -R            Print the RCS file name only.
   -h            Print only the "header" information.
