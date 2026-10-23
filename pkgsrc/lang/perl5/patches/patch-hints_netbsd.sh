$NetBSD: patch-hints_netbsd.sh,v 1.11 2024/11/16 11:54:24 wiz Exp $

Better defaults for paths.

EmberBSD (AI-assisted): preserve target probes, architecture and loader paths.
Not submitted upstream.

--- hints/netbsd.sh.orig
+++ hints/netbsd.sh
@@ -3,9 +3,15 @@
 # Please check with packages@netbsd.org before making modifications
 # to this file.
 
+# Target hardware and loader paths must not come from the build host.
+case "$usecrosscompile" in
+define) netbsd_arch=${targetarch%%-*} ;;
+*) netbsd_arch=`uname -m` ;;
+esac
+
 case "$archname" in
 '')
-    archname=`uname -m`-${osname}
+    archname=${netbsd_arch}-${osname}
     ;;
 esac
 
@@ -19,7 +25,7 @@
 	usedl="$undef"
 	;;
 *)
-	case `uname -m` in
+	case "$netbsd_arch" in
 	pmax)
 		# NetBSD 1.3 and 1.3.1 on pmax shipped an `old' ld.so,
 		# which will not work.
@@ -30,7 +36,8 @@
 		esac
 		;;
 	esac
-	if test -f /usr/libexec/ld.elf_so; then
+	if test -f "$sysroot/libexec/ld.elf_so" ||
+	   test -f "$sysroot/usr/libexec/ld.elf_so"; then
 		# ELF
 		d_dlopen=$define
 		d_dlerror=$define
@@ -62,7 +69,7 @@
 			ccdlflags="-Wl,-E $ccdlflags"
 			;;
 		esac
-	elif test -f /usr/libexec/ld.so; then
+	elif test -f "$sysroot/usr/libexec/ld.so"; then
 		# a.out
 		d_dlopen=$define
 		d_dlerror=$define
@@ -200,10 +207,11 @@
 EOCBU
 
 # Set sensible defaults for NetBSD: look for local software in
-# /usr/pkg (NetBSD Packages Collection) and in /usr/local.
+# /usr/local, plus the build prefix, which might or might not be
+# /usr/pkg.
 #
-loclibpth="/usr/pkg/lib /usr/local/lib"
-locincpth="/usr/pkg/include /usr/local/include"
+loclibpth="${prefix}/lib /usr/local/lib"
+locincpth="${prefix}/include /usr/local/include"
 case "$rpathflag" in
 '')
 	ldflags=
@@ -216,7 +224,7 @@
 	;;
 esac
 
-case `uname -m` in
+case "$netbsd_arch" in
 alpha)
     echo 'int main() {}' > try.c
     gcc=`${cc:-cc} -v -c try.c 2>&1|grep 'gcc version egcs-2'`
@@ -241,7 +249,7 @@
 esac
 
 # NetBSD/sparc 1.5.3/1.6.1 dumps core in the semid_ds test of Configure.
-case `uname -m` in
+case "$netbsd_arch" in
 sparc) d_semctl_semid_ds=undef ;;
 esac
 
