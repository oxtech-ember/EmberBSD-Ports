$NetBSD$

Origin: EmberBSD (AI-assisted); preserve OS portability and build routing.

--- main.c.orig
+++ main.c
@@ -194,7 +194,7 @@
 		  fatal("File '",s,"' not accessible");
 		nfils++;
 	    }
-	    xargc++, *xargv--;		/* Adjust argv/argc */
+	    xargc++, xargv--;		/* Adjust argv/argc */
 	    if (nfils < 1)
 	      fatal("Missing filename for -s",(char *)0,(char *)0);
 	    action = A_SEND;
@@ -209,7 +209,7 @@
 #endif /* DEBUG */
 	    if (*(xp+1))
 	      fatal("Invalid argument bundling",(char *)0,(char *)0);
-	    *xargv++, xargc--;
+	    xargv++, xargc--;
 	    if ((xargc < 1) || (**xargv == '-'))
 	      fatal("Missing option argument",(char *)0,(char *)0);
 	    s = *xargv;
@@ -260,7 +260,7 @@
 	  case 'p':			/* Parity */
 	    if (*(xp+1))
 	      fatal("Invalid argument bundling",(char *)0,(char *)0);
-	    *xargv++, xargc--;
+	    xargv++, xargc--;
 	    if ((xargc < 1) || (**xargv == '-'))
 	      fatal("Missing parity",(char *)0,(char *)0);
 	    switch(x = **xargv) {
@@ -290,7 +290,7 @@
     return(action);
 }
 
-void
+int
 main(int argc, char ** argv) {
     int status, rx_len, i, x;
     char c;
@@ -427,8 +427,8 @@
   date, size, and bytes transferred so far.  These can be used in a
   file-transfer progress display, log, etc.
 */
-	    debug(DB_LOG,"NAME",r.filename ? (char *)r.filename : "(NULL)",0);
-	    debug(DB_LOG,"DATE",r.filedate ? (char *)r.filedate : "(NULL)",0);
+	    debug(DB_LOG,"NAME",r.filename ? r.filename : (UCHAR *)"(NULL)",0);
+	    debug(DB_LOG,"DATE",r.filedate,0);
 	    debug(DB_LOG,"SIZE",0,r.filesize);
 	    debug(DB_LOG,"STATE",0,r.status);
 	    debug(DB_LOG,"SOFAR",0,r.sofar);
