$NetBSD$

A top-level closing brace ends the previous declaration buffer; do not carry
it across skipped preprocessor branches into the next declaration.

--- cf/make-proto.pl.orig
+++ cf/make-proto.pl
@@ -213,8 +213,10 @@
     if(/\}/){
 	$brace--;
     }
     if(/^\}/){
 	$brace = 0;
+	$line = "";
+	next;
     }
     if($brace == 0) {
 	$line = $line . " " . $_;
     }
