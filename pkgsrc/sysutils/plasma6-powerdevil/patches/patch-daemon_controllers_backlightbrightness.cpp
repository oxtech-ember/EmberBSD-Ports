$NetBSD$

NetBSD has no sysfs backlight path. Use the sysctl values from the
helper, as FreeBSD does (EmberBSD).

--- daemon/controllers/backlightbrightness.cpp.orig	2026-10-28 12:00:00.000000000 +0000
+++ daemon/controllers/backlightbrightness.cpp
@@ -67,8 +67,8 @@
             }
             int maxBrightness = brightnessMaxJob->data()[u"brightnessmax"_s].toInt();
 
-#ifdef Q_OS_FREEBSD
-            // FreeBSD doesn't have the sysfs interface that the bits below expect;
+#if defined(Q_OS_FREEBSD) || defined(Q_OS_NETBSD)
+            // FreeBSD and NetBSD don't have the sysfs interface that the bits below expect;
             // the sysfs calls always fail, leading to detectionFinished(false) emission.
             // Skip that command and carry on with the information that we do have.
             if (maxBrightness > 0) {
@@ -114,7 +114,7 @@
     , m_executedBrightness(observedBrightness)
     , m_maxBrightness(maxBrightness)
 {
-#ifndef Q_OS_FREEBSD
+#if !defined(Q_OS_FREEBSD) && !defined(Q_OS_NETBSD)
     // Kernel doesn't send uevent for leds-class devices, or at least that's what commit 26a48f9db
     // claimed (although the monitored subsystem was already hardcoded to "backlight" then).
     // Keep track of backlight devices for changes not initiated by this class.
