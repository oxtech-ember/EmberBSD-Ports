$NetBSD$

Origin: EmberBSD (AI-assisted); preserve OS portability and build routing.

--- kermit.h.orig
+++ kermit.h
@@ -383,7 +383,7 @@
     int (*readf)(struct k_data *);	         /* read-file function  */
     int (*writef)(struct k_data *,UCHAR *, int); /* write-file function */
     int (*closef)(struct k_data *,UCHAR,int);    /* close-file function */
-    int (*dbf)(int,UCHAR *,UCHAR *,long);  /* debug function */
+    void (*dbf)(int,UCHAR *,UCHAR *,long);  /* debug function */
     UCHAR * zinbuf;			/* Input file buffer itself */
     int zincnt;				/* Input buffer position */
     int zinlen;				/* Length of input file buffer */
