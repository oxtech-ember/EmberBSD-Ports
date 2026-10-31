$NetBSD$

Remove a write-only variable to build with modern Clang diagnostics.
Origin: EmberBSD contributors (AI-assisted).

--- src/lrz.c.orig
+++ src/lrz.c
@@ -108,7 +108,6 @@
 static char Lzmanag;		/* Local file management request */
 static char zconv;		/* ZMODEM file conversion request */
 static char zmanag;		/* ZMODEM file management request */
-static char ztrans;		/* ZMODEM file transport request */
 bool Zctlesc;		/* Encode control characters */
 unsigned int Zrwindow = 1400;	/* RX window size (controls garbage count) */
 
@@ -1683,7 +1682,6 @@
 				skip_if_not_found=true;
 			}
 			zmanag = Rxhdr[ZF1];
-			ztrans = Rxhdr[ZF2];
 			tryzhdrtype = ZRINIT;
 			c = zrdata(secbuf, LRZSZ_MAX_SUBPACKET_LEN, &bytes_in_block);
 			io_mode(0,3);
