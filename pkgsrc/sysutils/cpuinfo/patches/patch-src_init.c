$NetBSD$

Preserve basic NetBSD support from https://github.com/pytorch/cpuinfo/pull/315.

--- src/init.c.orig
+++ src/init.c
@@ -24,7 +24,7 @@
 #if CPUINFO_ARCH_X86 || CPUINFO_ARCH_X86_64
 #if defined(__MACH__) && defined(__APPLE__)
 	pthread_once(&init_guard, &cpuinfo_x86_mach_init);
-#elif defined(__FreeBSD__)
+#elif defined(__FreeBSD__) || defined(__NetBSD__)
 	pthread_once(&init_guard, &cpuinfo_x86_freebsd_init);
 #elif defined(__linux__)
 	pthread_once(&init_guard, &cpuinfo_x86_linux_init);
