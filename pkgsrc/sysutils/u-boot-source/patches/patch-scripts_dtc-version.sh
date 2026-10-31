$NetBSD$

--- a/scripts/dtc-version.sh
+++ b/scripts/dtc-version.sh
@@ -15,7 +15,7 @@
 	exit 1
 fi
 
-if ! which $dtc > /dev/null 2>&1 ; then
+if ! command -v "$dtc" > /dev/null 2>&1 ; then
 	echo "Error: Cannot find dtc: $dtc"
 	exit 1
 fi
