$NetBSD$

Origin: EmberBSD (AI-assisted); preserve OS portability and build routing.

--- kermit.c.orig
+++ kermit.c
@@ -100,7 +100,7 @@
     int datalen;                        /* Length of packet data field */
     UCHAR *p;                           /* Pointer to packet data field */
     UCHAR *q;                           /* Pointer to data to be checked */
-    UCHAR *s;				/* Worker string pointer */
+    UCHAR *s = (UCHAR *)0;		/* Worker string pointer */
     UCHAR c, t;                         /* Worker chars */
     UCHAR pbc[4];                       /* Copy of packet block check */
     short seq, prev;			/* Copies of sequence numbers */
@@ -1287,11 +1287,11 @@
 
 STATIC int
 gattr(struct k_data * k, UCHAR * s, struct k_response * r) {
-    long fsize, fsizek;                 /* File size */
+    long fsize = -1L, fsizek = -1L;    /* File size */
     UCHAR c;                            /* Workers */
     int aln, i, rc;
 
-    UCHAR sizebuf[SIZEBUFL];
+    UCHAR sizebuf[SIZEBUFL+1];
 
     rc = -1;
     while ((c = *s++)) {		/* Get attribute tag */
@@ -1316,7 +1316,7 @@
             break;
 
           case '#':                     /* File creation date */
-            for (i = 0; (i < aln) && (i < DATE_MAX); i++)
+            for (i = 0; (i < aln) && (i < DATE_MAX - 1); i++)
               r->filedate[i] = *s++;    /* Copy it into a static string */
             if (i < aln) s += (aln - i);
             r->filedate[i] = '\0';
