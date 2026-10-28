$NetBSD$

Combine BSD platform changes and preserve correct current-thread stack bounds.
Origin: NetBSD pkgsrc Node and Chromium, EmberBSD Ports Electron overlay.
Use native integer thread IDs to avoid truncating pthread pointers.

--- src/base/platform/platform-posix.cc.orig
+++ src/base/platform/platform-posix.cc
@@ -9,6 +9,9 @@
 #include <errno.h>
 #include <limits.h>
 #include <pthread.h>
+#if defined(__NetBSD__)
+#include <lwp.h>
+#endif
 
 #include "src/base/fpu.h"
 #include "src/base/logging.h"
@@ -78,8 +81,10 @@
 #include <sys/syscall.h>
 #endif
 
-#if V8_OS_FREEBSD || V8_OS_DARWIN || V8_OS_OPENBSD || V8_OS_SOLARIS
+#if V8_OS_FREEBSD || V8_OS_DARWIN || V8_OS_BSD || V8_OS_SOLARIS
+#ifndef MAP_ANONYMOUS
 #define MAP_ANONYMOUS MAP_ANON
+#endif
 #endif
 
 #if defined(V8_OS_SOLARIS)
@@ -359,6 +364,13 @@
   }
 }
 
+#if V8_OS_OPENBSD
+// Allow OpenBSD's mmap to select a random address on OpenBSD
+// static
+void* OS::GetRandomMmapAddr() {
+  return nullptr;
+}
+#else
 // static
 void* OS::GetRandomMmapAddr() {
   uintptr_t raw_addr;
@@ -455,8 +467,13 @@
 #endif
 #endif
 #endif
+
+#if V8_OS_NETBSD
+  raw_addr = 0;
+#endif
   return reinterpret_cast<void*>(raw_addr);
 }
+#endif
 
 // TODO(bbudge) Move Cygwin and Fuchsia stuff into platform-specific files.
 #if !V8_OS_CYGWIN && !V8_OS_FUCHSIA
@@ -772,7 +789,7 @@
 #if !V8_OS_ZOS
 // static
 bool OS::HasLazyCommits() {
-#if V8_OS_AIX || V8_OS_LINUX || V8_OS_DARWIN
+#if V8_OS_AIX || V8_OS_LINUX || V8_OS_DARWIN || V8_OS_BSD
   return true;
 #else
   // TODO(bbudge) Return true for all POSIX platforms.
@@ -923,6 +940,10 @@
   return static_cast<int>(syscall(__NR_gettid));
 #elif V8_OS_ANDROID
   return static_cast<int>(gettid());
+#elif V8_OS_NETBSD
+  return static_cast<int>(_lwp_self());
+#elif V8_OS_FREEBSD
+  return pthread_getthreadid_np();
 #elif V8_OS_AIX
   return static_cast<int>(thread_self());
 #elif V8_OS_FUCHSIA
@@ -1229,7 +1250,11 @@
       stack_size_(options.stack_size()),
       priority_(options.priority()),
       start_semaphore_(nullptr) {
+#if V8_OS_NETBSD
+  const int min_stack_size = sysconf(_SC_THREAD_STACK_MIN);
+#else
   const int min_stack_size = static_cast<int>(PTHREAD_STACK_MIN);
+#endif
   if (stack_size_ > 0) stack_size_ = std::max(stack_size_, min_stack_size);
   set_name(options.name());
 }
@@ -1244,7 +1269,7 @@
   pthread_set_name_np(pthread_self(), name);
 #elif V8_OS_NETBSD
   static_assert(Thread::kMaxThreadNameLength <= PTHREAD_MAX_NAMELEN_NP);
-  pthread_setname_np(pthread_self(), "%s", name);
+  pthread_setname_np(pthread_self(), "%s", (void *)name);
 #elif V8_OS_DARWIN
   // pthread_setname_np is only available in 10.6 or later, so test
   // for it at runtime.
@@ -1451,8 +1476,7 @@
     DCHECK(MainThreadIsCurrentThread());
     return nullptr;
   }
-  void* stack_start = reinterpret_cast<uint8_t*>(stack.ss_sp) + stack.ss_size;
-  return stack_start;
+  return stack.ss_sp;
 #else
   pthread_attr_t attr;
   int error = pthread_getattr_np(pthread_self(), &attr);
@@ -1497,7 +1521,7 @@
     DCHECK(MainThreadIsCurrentThread());
     return nullptr;
   }
-  return stack.ss_sp;
+  return reinterpret_cast<uint8_t*>(stack.ss_sp) - stack.ss_size;
 #else
 // For most libcs, pthread_getattr_np() returns the the stack reserved
 // limit on the main thread, but musl only returns the current high-water
--- src/base/platform/platform-openbsd.cc.orig
+++ src/base/platform/platform-openbsd.cc
@@ -34,6 +34,48 @@
 
 namespace v8 {
 namespace base {
+
+#ifdef __arm__
+
+bool OS::ArmUsingHardFloat() {
+  // GCC versions 4.6 and above define __ARM_PCS or __ARM_PCS_VFP to specify
+  // the Floating Point ABI used (PCS stands for Procedure Call Standard).
+  // We use these as well as a couple of other defines to statically determine
+  // what FP ABI used.
+  // GCC versions 4.4 and below don't support hard-fp.
+  // GCC versions 4.5 may support hard-fp without defining __ARM_PCS or
+  // __ARM_PCS_VFP.
+
+#define GCC_VERSION (__GNUC__ * 10000                                          \
+                     + __GNUC_MINOR__ * 100                                    \
+                     + __GNUC_PATCHLEVEL__)
+#if GCC_VERSION >= 40600
+#if defined(__ARM_PCS_VFP)
+  return true;
+#else
+  return false;
+#endif
+
+#elif GCC_VERSION < 40500
+  return false;
+
+#else
+#if defined(__ARM_PCS_VFP)
+  return true;
+#elif defined(__ARM_PCS) || defined(__SOFTFP__) || defined(__SOFTFP) || \
+      !defined(__VFP_FP__)
+  return false;
+#else
+#error "Your version of GCC does not report the FP ABI compiled for."          \
+       "Please report it on this issue"                                        \
+       "http://code.google.com/p/v8/issues/detail?id=2140"
+
+#endif
+#endif
+#undef GCC_VERSION
+}
+
+#endif  // def __arm__
 
 TimezoneCache* OS::CreateTimezoneCache() {
   return new PosixDefaultTimezoneCache();
