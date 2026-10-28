$NetBSD$

Origin: EmberBSD (AI-assisted); preserve OS portability and build routing.

--- unixio.c.orig
+++ unixio.c
@@ -102,10 +102,12 @@
       case DB_PKT:			/* Log a packet */
 	/* (fill in later, fall thru for now...) */
       case DB_LOG:			/* Write label and string or number */
-	if (sval && dp)
-	  fprintf(dp,"%s[%s]\n",label,sval);
-	else
-	  fprintf(dp,"%s=%ld\n",label,nval);
+	if (dp) {
+	    if (sval)
+	      fprintf(dp,"%s[%s]\n",label,sval);
+	    else
+	      fprintf(dp,"%s=%ld\n",label,nval);
+	}
 	return;
       case DB_CLS:			/* Close debug log */
 	if (dp) {
@@ -415,7 +417,7 @@
 fileinfo(struct k_data * k,
 	 UCHAR * filename, UCHAR * buf, int buflen, short * type, short mode) {
     struct stat statbuf;
-    struct tm * timestamp, * localtime();
+    struct tm * timestamp;
 
 #ifdef F_SCAN
     FILE * fp;				/* File scan pointer */
