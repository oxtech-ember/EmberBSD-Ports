$NetBSD$

Remove write-only variables and correct signed debug formatting.
Origin: EmberBSD contributors (AI-assisted).

--- src/lsz.c.orig
+++ src/lsz.c
@@ -94,7 +94,6 @@
 
 static char *txbuf;
 
-static long vpos = 0;			/* Number of bytes read from file */
 
 static char Lastrx;
 static char Crcflg;
@@ -129,7 +128,6 @@
 static int Cmdack1;		/* Rx ACKs command, then do it */
 static int Exitcode;
 static size_t Lastsync;		/* Last offset to which we got a ZRPOS */
-static int Beenhereb4;		/* How many times we've been ZRPOS'd same place */
 /* set when an abort arm has answered a receiver's ZABORT/ZFERR with the
  * spec-required ZFIN sequence (zmodem-wip.txt §4): the session is then
  * already ended cleanly, and main() must not append a cancel sequence */
@@ -762,7 +760,6 @@
 			setvbuf(input_f,s,_IOFBF,last_length);
 		}
 	}
-	vpos = 0;
 	/* fstat must succeed: its fields are transmitted below as the file's
 	 * metadata (mode/mtime/size). A failure used to send uninitialized
 	 * memory - a garbage size in particular can make the receiver
@@ -1800,7 +1797,6 @@
 
 	Lrxpos = 0;
 	junkcount = 0;
-	Beenhereb4 = 0;
 	last_txpos = 0;
 	low_bps = 0;
 	not_printed = 0;
@@ -2232,7 +2228,7 @@
             fprintf(stderr,"calc_blklen changed Txwindow from %u to %u\n",old_Txwindow,Txwindow);
         }
         if (ret!=last_blklen && last_blklen) {
-            fprintf(stderr,"calc_blklen changed blklen from %u to %u\n",last_blklen,ret);
+            fprintf(stderr,"calc_blklen changed blklen from %d to %d\n",last_blklen,ret);
         }
     }
     last_blklen=ret;
