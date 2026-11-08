$NetBSD$

Select the NetBSD CPU plugin.

--- plugins/cpu/cpuplugin.cpp.orig
+++ plugins/cpu/cpuplugin.cpp
@@ -14,6 +14,9 @@
 
 #include "freebsdcpuplugin.h"
 #include "linuxcpuplugin.h"
+#ifdef Q_OS_NETBSD
+#include "netbsdcpuplugin.h"
+#endif
 
 CpuPluginPrivate::CpuPluginPrivate(CpuPlugin *q)
     : m_container(new KSysGuard::SensorContainer(QStringLiteral("cpu"), i18n("CPUs"), q))
@@ -26,6 +29,8 @@
     , d(new LinuxCpuPluginPrivate(this))
 #elif defined Q_OS_FREEBSD
     , d(new FreeBsdCpuPluginPrivate(this))
+#elif defined Q_OS_NETBSD
+    , d(new NetBsdCpuPluginPrivate(this))
 #else
     , d(new CpuPluginPrivate(this))
 #endif
