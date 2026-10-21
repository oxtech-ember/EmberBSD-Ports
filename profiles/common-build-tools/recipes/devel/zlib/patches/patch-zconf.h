$NetBSD$

zlib 1.3.2 tests HAVE_UNISTD_H and HAVE_STDARG_H with "#if NAME-0".
Consumers that build with -Werror=undef, such as KDE Frameworks tests,
reject the installed header when a name is undefined. Test definition
first. An undefined or zero value still leaves the Z_HAVE_* macro unset.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- zconf.h.orig
+++ zconf.h
@@ -443,11 +443,11 @@
    typedef unsigned long z_crc_t;
 #endif
 
-#if HAVE_UNISTD_H-0     /* may be set to #if 1 by ./configure */
+#if defined(HAVE_UNISTD_H) && HAVE_UNISTD_H-0 /* may be set to #if 1 by ./configure */
 #  define Z_HAVE_UNISTD_H
 #endif
 
-#if HAVE_STDARG_H-0     /* may be set to #if 1 by ./configure */
+#if defined(HAVE_STDARG_H) && HAVE_STDARG_H-0 /* may be set to #if 1 by ./configure */
 #  define Z_HAVE_STDARG_H
 #endif
 
