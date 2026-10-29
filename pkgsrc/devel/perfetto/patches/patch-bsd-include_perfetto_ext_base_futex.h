Do not use Linux futexes on BSD. BSD builds set the Linux build flag,
but they do not have linux/futex.h or SYS_futex. Use the existing
fallback.

Origin: EmberBSD contributors (AI-assisted); not submitted upstream.

--- include/perfetto/ext/base/futex.h
+++ include/perfetto/ext/base/futex.h
@@ -24,8 +24,9 @@
 // Whether this build implements FutexWait() and FutexWake(). It does not check
 // runtime restrictions, such as a sandbox that blocks the system call.
 // TODO(rsavitski): Add support for other platforms.
-#define PERFETTO_HAS_FUTEX()                            \
-  (PERFETTO_BUILDFLAG(PERFETTO_OS_LINUX_BUT_NOT_QNX) || \
+#define PERFETTO_HAS_FUTEX()                             \
+  ((PERFETTO_BUILDFLAG(PERFETTO_OS_LINUX_BUT_NOT_QNX) && \
+    !PERFETTO_BUILDFLAG(PERFETTO_OS_BSD)) ||             \
    PERFETTO_BUILDFLAG(PERFETTO_OS_ANDROID))
 
 namespace perfetto::base {
