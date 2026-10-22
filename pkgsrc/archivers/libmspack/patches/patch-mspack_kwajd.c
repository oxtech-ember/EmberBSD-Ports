$NetBSD$

Initialize KWAJ cleanup pointers before a header error.
From upstream commit 4d868504114346aa767d435fbb89a8b76603493f (2026-06-15).
Stuart Caie credits Yukimura Aneha for the report, samples and patch.
https://github.com/kyz/libmspack/commit/4d868504114346aa767d435fbb89a8b76603493f

--- mspack/kwajd.c.orig
+++ mspack/kwajd.c
@@ -160,6 +160,11 @@ static int kwajd_read_headers(struct mspack_system *sys,
     unsigned char buf[16];
     int i;
 
+
+    /* initialise pointers */
+    hdr->filename = NULL;
+    hdr->extra    = NULL;
+
     /* read in the header */
     if (sys->read(fh, &buf[0], kwajh_SIZEOF) != kwajh_SIZEOF) {
         return MSPACK_ERR_READ;
@@ -177,8 +182,6 @@ static int kwajd_read_headers(struct mspack_system *sys,
     hdr->data_offset  = EndGetI16(&buf[kwajh_DataOffset]);
     hdr->headers      = EndGetI16(&buf[kwajh_Flags]);
     hdr->length       = 0;
-    hdr->filename     = NULL;
-    hdr->extra        = NULL;
     hdr->extra_length = 0;
 
     /* optional headers */
