$NetBSD$

Regenerate the build files without running configure when NOCONFIGURE
is set, so the pkgsrc configure step runs it with its own arguments.

--- autogen.sh.orig
+++ autogen.sh
@@ -170,6 +170,11 @@
 echo "  autoconf"
 autoconf
 
+# EmberBSD: NOCONFIGURE=1 regenerates the build files only.
+if test -n "$NOCONFIGURE"; then
+	exit 0
+fi
+
 if test -z "$*"; then
         echo "I am going to run ./configure with no arguments - if you wish "
         echo "to pass any to it, please specify them on the $0 command line."
