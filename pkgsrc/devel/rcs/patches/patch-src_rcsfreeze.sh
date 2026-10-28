# Origin: EmberBSD (AI-assisted).
Use the caller-selected tools and a portable mktemp template.

--- src/rcsfreeze.sh.orig
+++ src/rcsfreeze.sh
@@ -58,9 +58,6 @@
 if [ x"$1" = x--help ] ; then usage ; exit 0 ; fi
 if [ x"$1" = x--version ] ; then echo "$version" ; exit 0 ; fi
 
-PATH=/usr/local/bin:/bin:/usr/bin:/usr/ucb:$PATH
-export PATH
-
 DATE=`date` || exit
 # Check whether we have an RCS subdirectory, so we can have the right
 # prefix for our paths.
@@ -92,8 +89,8 @@
 
 # Stamp the logfile. Because we order the logfile the most recent
 # first we will have to save everything right now in a temporary file.
-TMPLOG=`mktemp -t` || exit
-trap 'rm -f $TMPLOG; exit 1' 1 2 13 15
+TMPLOG=`mktemp "${TMPDIR:-/tmp}/rcsfreeze.XXXXXXXXXX"` || exit
+trap 'rm -f "$TMPLOG"; exit 1' 1 2 13 15
 # Now ask for a log message, continously add to the log file
 (
 	echo "Version: $SYMREVNAME($SYMREV), Date: $DATE
@@ -108,11 +105,11 @@
 	echo "-----------
 " &&
 	cat $LOGFILE
-) >$TMPLOG &&
+) >"$TMPLOG" &&
 
 # combine old and new logfiles
-cp $TMPLOG $LOGFILE &&
-rm -f $TMPLOG &&
+cp "$TMPLOG" "$LOGFILE" &&
+rm -f "$TMPLOG" &&
 
 # Now the real work begins by assigning a symbolic revision number
 # to each rcs file.  Take the most recent version on the default branch.
