$NetBSD$

Use selected native tools and check preprocessing before generation.

--- migcom.tproj/mig.sh.orig
+++ migcom.tproj/mig.sh
@@ -63,25 +63,15 @@
 	return 1
 }
 
-scriptPath=$(realpath "$0")
-scriptRoot=$(dirname "$scriptPath")
-migcomPath=$(realpath "${scriptRoot}/../libexec/migcom")
-
 if [ -n "${SDKROOT}" ]; then
 	sdkRoot="${SDKROOT}";
 fi
 
-if [ -z "${MIGCC}" ]; then
-  xcrunPath="/usr/bin/xcrun"
-  if [ -x "${xcrunPath}" ]; then
-    MIGCC=`"${xcrunPath}" -sdk "$sdkRoot" -find cc`
-  else
-    MIGCC=$(realpath "${scriptRoot}/cc")
-  fi
-fi
+: "${MIGCC:?MIGCC must select the compiler}"
+: "${MIGCOM:?MIGCOM must select migcom}"
 
 C=${MIGCC}
-M=${MIGCOM-${migcomPath}}
+M=${MIGCOM}
 
 if [ $# -eq 1 ] && [ "$1" = "-version" ] ; then
 	"$M" "$@"
@@ -91,9 +81,9 @@
 cppflags="-D__MACH30__"
 
 files=
-arch=`/usr/bin/arch`
-
-WORKTMP=`/usr/bin/mktemp -d "${TMPDIR:-/tmp}/mig.XXXXXX"`
+arch=`uname -m`
+
+WORKTMP=`mktemp -d "${TMPDIR:-/tmp}/mig.XXXXXX"`
 if [ $? -ne 0 ]; then
       echo "Failure creating temporary work directory: ${WORKTMP}"
       echo "Exiting..."
@@ -177,16 +167,22 @@
     if [ -n "$MIG_TRACE_HEADERS" ]
     then
       env CC_PRINT_HEADERS_FORMAT=json CC_PRINT_HEADERS_FILTERING=only-direct-system CC_PRINT_HEADERS_FILE="$MIG_TRACE_HEADERS" \
-        "$C" -E -arch ${arch} "${target[@]}" "${cppflags[@]}" -I "${sourcedir}" "${iSysRootParm[@]}" "${temp}.c" | "$M" "${migflags[@]}"
+        "$C" -E -arch ${arch} "${target[@]}" "${cppflags[@]}" -I "${sourcedir}" "${iSysRootParm[@]}" "${temp}.c" > "${temp}.i"
     else
       env -u CC_PRINT_HEADERS_FORMAT \
-        "$C" -E -arch ${arch} "${target[@]}" "${cppflags[@]}" -I "${sourcedir}" "${iSysRootParm[@]}" "${temp}.c" | "$M" "${migflags[@]}"
+        "$C" -E -arch ${arch} "${target[@]}" "${cppflags[@]}" -I "${sourcedir}" "${iSysRootParm[@]}" "${temp}.c" > "${temp}.i"
     fi
     if [ $? -ne 0 ]
     then
-      rm -rf "${temp}.c" "${temp}.d" "${WORKTMP}"
-      exit 1
-    fi
+      rm -rf "${WORKTMP}"
+      exit 1
+    fi
+    if ! "$M" "${migflags[@]}" < "${temp}.i"
+    then
+      rm -rf "${WORKTMP}"
+      exit 1
+    fi
+    rm -f "${temp}.i"
     if [ "${sawMD}" -a -f "${temp}.d" ]
     then
 	deps=
@@ -230,6 +226,6 @@
     rm -f "${temp}.c"
 done
 
-/bin/rmdir "${WORKTMP}"
+rmdir "${WORKTMP}"
 exit 0
 
