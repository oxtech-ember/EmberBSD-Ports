$NetBSD$

Origin: EmberBSD (AI-assisted); preserve OS portability and build routing.

--- unixio.c.orig
+++ unixio.c
@@ -78,13 +78,13 @@
     if (fc != DB_OPN && !xdebug)
       return;
     if (!label)
-      label = "";
+      label = (UCHAR *)"";
 
     switch (fc) {			/* Function code */
       case DB_OPN:			/* Open debug log */
 	if (dp) fclose(dp);
-	if (!*label) label = "debug.log";
-	dp = fopen(label,"w");
+	if (!*label) label = (UCHAR *)"debug.log";
+	dp = fopen((const char *)label,"w");
 	if (!dp) {
 	    dp = stderr;
 	} else {
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
@@ -249,7 +251,7 @@
   version might be driven by the value of the packet-length field.
 */
 #ifdef DEBUG
-    char * p2;
+    UCHAR * p2;
 #endif	/* DEBUG */
 
 #ifdef F_CTRLC
@@ -351,7 +353,7 @@
 
     switch (mode) {
       case 1:				/* Read */
-	if (!(ifile = fopen(s,"r"))) {
+	if (!(ifile = fopen((const char *)s,"r"))) {
 	    debug(DB_LOG,"openfile read error",s,0);
 	    return(X_ERROR);
 	}
@@ -363,7 +365,7 @@
 	return(X_OK);
 
       case 2:				/* Write (create) */
-        ofile = creat(s,0644);
+        ofile = creat((const char *)s,0644);
 	if (ofile < 0) {
 	    debug(DB_LOG,"openfile write error",s,0);
 	    return(X_ERROR);
@@ -415,7 +417,7 @@
 fileinfo(struct k_data * k,
 	 UCHAR * filename, UCHAR * buf, int buflen, short * type, short mode) {
     struct stat statbuf;
-    struct tm * timestamp, * localtime();
+    struct tm * timestamp;
 
 #ifdef F_SCAN
     FILE * fp;				/* File scan pointer */
@@ -427,10 +429,10 @@
     buf[0] = '\0';
     if (buflen < 18)
       return(X_ERROR);
-    if (stat(filename,&statbuf) < 0)
+    if (stat((const char *)filename,&statbuf) < 0)
       return(X_ERROR);
     timestamp = localtime(&(statbuf.st_mtime));
-    sprintf(buf,"%04d%02d%02d %02d:%02d:%02d",
+    sprintf((char *)buf,"%04d%02d%02d %02d:%02d:%02d",
 	    timestamp->tm_year + 1900,
             timestamp->tm_mon + 1,
             timestamp->tm_mday,
@@ -451,7 +453,7 @@
 */
     if (!mode) {			/* File type determination requested */
 	int isbinary = 1;
-	fp = fopen(filename,"r");	/* Open the file for scanning */
+	fp = fopen((const char *)filename,"r");	/* Open the file for scanning */
 	if (fp) {
 	    int n = 0, count = 0;
 	    char c, * p;
@@ -603,7 +605,7 @@
 		   (c == 'D')) {	/* This file was incomplete */
 	    if (k->filename) {
 		debug(DB_LOG,"deleting incomplete",k->filename,0);
-		unlink(k->filename);	/* Delete it. */
+		unlink((const char *)k->filename);	/* Delete it. */
 	    }
 	}
 	break;
