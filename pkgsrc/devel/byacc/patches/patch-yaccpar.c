$NetBSD$

Preserve NetBSD and EmberBSD byacc integration changes from the OS source.
Origin: NetBSD and EmberBSD (AI-assisted); not submitted upstream.

--- yaccpar.c.orig
+++ yaccpar.c
@@ -1,3 +1,5 @@
+/*	$NetBSD: yaccpar.c,v 1.8 2024/09/14 21:29:02 christos Exp $	*/
+
 /* This file generated automatically using
  * @Id: skel2c,v 1.4 2016/06/07 00:26:09 tom Exp @
  */
@@ -16,7 +18,7 @@
 
 const char *const banner[] =
 {
-    "/* original parser id follows */",
+    "/* EmberBSD parser skeleton; original parser id follows. */",
     "/* yysccsid[] = \"@(#)yaccpar	1.9 (Berkeley) 02/21/93\" */",
     "/* (use YYMAJOR/YYMINOR for ifdefs dependent on parser version) */",
     "",
@@ -230,6 +232,7 @@
     "    /* yym is set below */",
     "    /* yyn is set below */",
     "    yynerrs = 0;",
+    "    (void)yynerrs; /* User actions may omit the error count. */",
     "    yyerrflag = 0;",
     "    yychar = YYEMPTY;",
     "    yystate = 0;",
