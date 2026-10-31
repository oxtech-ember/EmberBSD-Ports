$NetBSD$

Probe integer sizes with unsigned arithmetic. A signed overflow made
the cross bound non-constant; clang++ accepted it as a variable length
array and reported int_bitsize 31, so intparam.h stopped the build:
"int and unsigned int have different sizes".

--- m4/intparam.m4.orig
+++ m4/intparam.m4
@@ -229,13 +229,16 @@
 dnl puts into variable the determined bitsize of the type.
 AC_DEFUN([CL_INTPARAM_BITSIZE],
 [
-  n=1; x="($1)2"
+  dnl Multiply in unsigned long long: a signed overflow makes the bound
+  dnl non-constant, and a C++ compiler that accepts variable length
+  dnl arrays would then report a size one bit short.
+  n=1; x="(unsigned long long)2"
   while true; do
     AC_COMPILE_IFELSE([AC_LANG_PROGRAM([],
       [[typedef int verify[2*(($1)($x) == 0) - 1];]])],
       [$2=$n; break;],
       [if test $n = 1000; then $2=; break; fi;])
-    n=`expr $n + 1`; x="$x * ($1)2"
+    n=`expr $n + 1`; x="$x * (unsigned long long)2"
   done
 ])
 
