$NetBSD$

Select the NetBSD network backend.

--- plugins/network/NetworkPlugin.cpp.orig
+++ plugins/network/NetworkPlugin.cpp
@@ -27,6 +27,9 @@
 #ifdef Q_OS_FREEBSD
 #include "SysctlBackend.h"
 #endif
+#ifdef Q_OS_NETBSD
+#include "NetBsdBackend.h"
+#endif
 class NetworkPrivate
 {
 public:
@@ -58,6 +61,9 @@
 #ifdef Q_OS_FREEBSD
     backendFunctions.emplace_back([](NetworkPlugin *parent) -> NetworkBackend* {return new SysctlBackend(parent);});
 #endif
+#ifdef Q_OS_NETBSD
+    backendFunctions.emplace_back([](NetworkPlugin *parent) -> NetworkBackend* {return new NetBsdNetworkBackend(parent);});
+#endif
     for (auto func : backendFunctions) {
         auto backend = func(this);
         if (backend->isSupported()) {
