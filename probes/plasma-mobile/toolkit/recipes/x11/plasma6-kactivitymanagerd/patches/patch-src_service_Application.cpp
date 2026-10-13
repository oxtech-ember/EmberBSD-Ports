$NetBSD$

Include the uniquely named generated package version header.
Keep Version.h and its D-Bus protocol version unchanged.
Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- src/service/Application.cpp.orig	2026-09-08 10:51:00.000000000 +0000
+++ src/service/Application.cpp
@@ -7,7 +7,7 @@
 // Self
 #include "Application.h"
 #include <kactivities-features.h>
-#include <version.h>
+#include <kactivitymanagerd_version.h>
 
 // Qt
 #include <QDBusConnection>
