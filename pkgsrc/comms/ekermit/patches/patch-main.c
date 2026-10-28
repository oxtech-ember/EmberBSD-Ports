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
