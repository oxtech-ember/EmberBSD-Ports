$NetBSD$

Remove a write-only variable to build with modern Clang diagnostics.
Origin: EmberBSD contributors (AI-assisted).

--- src/zm.c.orig
+++ src/zm.c
@@ -34,7 +34,6 @@
 unsigned char Txhdr[4];		/* Transmitted header */
 int Txfcs32;		/* true means send binary frames with 32 bit FCS */
 int Crc32t;		/* Display flag indicating 32 bit CRC being sent */
-static int Crc32;		/* Display flag indicating 32 bit CRC being received */
 int Znulls;		/* Number of nulls to send at beginning of ZDATA hdr */
 char Attn[ZATTNLEN+1];	/* Attention string rx sends to tx on err */
 
@@ -784,7 +783,6 @@
 				continue;
 			case ZBIN:
 				Rxframeind = ZBIN;
-				Crc32 = false;
 				c =  zrbhdr(hdr);
 				if (c==ERROR) {
 					stats_msg_invalid();
@@ -799,7 +797,6 @@
 				continue;
 			case ZBIN32:
 				Rxframeind = ZBIN32;
-				Crc32 = true;
 				c =  zrbhdr32(hdr);
 				if (c==ERROR) {
 					stats_msg_invalid();
@@ -814,7 +811,6 @@
 				continue;
 			case ZHEX:
 				Rxframeind = ZHEX;
-				Crc32 = false;
 				c =  zrhhdr(hdr);
 				if (c==ERROR) {
 					stats_msg_invalid();
