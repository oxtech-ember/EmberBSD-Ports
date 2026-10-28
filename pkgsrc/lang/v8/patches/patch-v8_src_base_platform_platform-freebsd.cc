$NetBSD$

Combine pkgsrc Node and Chromium FreeBSD platform fixes.
Origin: NetBSD pkgsrc Chromium and Node.js platform-freebsd patches.
Provide the current V8 reserved stack limit using FreeBSD pthread attributes.

--- src/base/platform/platform-freebsd.cc.orig
+++ src/base/platform/platform-freebsd.cc
@@ -43,14 +43,10 @@
   return new PosixDefaultTimezoneCache();
 }
 
-static unsigned StringToLong(char* buffer) {
-  return static_cast<unsigned>(strtol(buffer, nullptr, 16));
-}
-
 std::vector<OS::SharedLibraryAddress> OS::GetSharedLibraryAddresses() {
-  std::vector<SharedLibraryAddress> result;
+  std::vector<SharedLibraryAddress> address_result;
   int mib[4] = {CTL_KERN, KERN_PROC, KERN_PROC_VMMAP, getpid()};
-  size_t miblen = sizeof(mib) / sizeof(mib[0]);
+  unsigned int miblen = sizeof(mib) / sizeof(mib[0]);
   size_t buffer_size;
   if (sysctl(mib, miblen, nullptr, &buffer_size, nullptr, 0) == 0) {
     // Overallocate the buffer by 1/3 to account for concurrent
@@ -81,16 +77,21 @@
           } else {
             lib_name = std::string(path);
           }
-          result.push_back(SharedLibraryAddress(
+          address_result.push_back(SharedLibraryAddress(
+#if defined(__i386__) || defined(V8_OS_FREEBSD)
+              lib_name, static_cast<uintptr_t>(map->kve_start),
+              static_cast<uintptr_t>(map->kve_end)));
+#else
               lib_name, reinterpret_cast<uintptr_t>(map->kve_start),
               reinterpret_cast<uintptr_t>(map->kve_end)));
+#endif
         }
 
         start += ssize;
       }
     }
   }
-  return result;
+  return address_result;
 }
 
 void OS::SignalCodeMovingGC() {}
@@ -121,5 +122,17 @@
   return nullptr;
 }
 
+// static
+Stack::StackSlot Stack::ObtainCurrentThreadStackReservedLimit() {
+  pthread_attr_t attr;
+  if (pthread_attr_init(&attr) != 0) return nullptr;
+  void* base = nullptr;
+  size_t size;
+  int error = pthread_attr_get_np(pthread_self(), &attr);
+  if (!error) error = pthread_attr_getstack(&attr, &base, &size);
+  pthread_attr_destroy(&attr);
+  return error ? nullptr : base;
+}
+
 }  // namespace base
 }  // namespace v8
