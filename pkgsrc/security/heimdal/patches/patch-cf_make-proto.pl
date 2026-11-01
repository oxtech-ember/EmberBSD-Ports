$NetBSD$

A top-level closing brace ends the previous declaration buffer; do not carry
it across skipped preprocessor branches into the next declaration.

--- cf/make-proto.pl.orig
+++ cf/make-proto.pl
@@ -215,6 +215,8 @@
     }
     if(/^\}/){
 	$brace = 0;
+	$line = "";
+	next;
     }
     if($brace == 0) {
 	$line = $line . " " . $_;
