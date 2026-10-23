$NetBSD$

Reject missing udev properties.
SDL3 virtual devices can have no OS path.

--- kcms/gamecontroller/udevmatcher.cpp.orig
+++ kcms/gamecontroller/udevmatcher.cpp
@@ -47,7 +47,11 @@
         return devicePath;
     }
 
-    devicePath = udev_device_get_property_value(udevice.get(), kDevicePathKey.c_str());
+    const char *devpath = udev_device_get_property_value(udevice.get(), kDevicePathKey.c_str());
+    if (!devpath) {
+        return devicePath;
+    }
+    devicePath = devpath;
 
     // Walk the devpath looking for the ID
     size_t slash = devicePath.find_last_of('/');
