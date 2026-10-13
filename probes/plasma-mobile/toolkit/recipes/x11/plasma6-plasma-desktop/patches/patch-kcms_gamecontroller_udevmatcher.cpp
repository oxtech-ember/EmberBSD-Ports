$NetBSD$

Reject unsupported device paths and missing udev properties.
SDL3 virtual devices can have no OS path.

--- kcms/gamecontroller/udevmatcher.cpp.orig
+++ kcms/gamecontroller/udevmatcher.cpp
@@ -31,6 +31,8 @@
     } else if (lastPart.starts_with("event")) {
         // input devpaths end with eventXY
         snprintf(sys_path, sizeof(sys_path), "/sys/class/input/%s", lastPart.c_str());
+    } else {
+        return devicePath;
     }
     std::unique_ptr<struct udev, decltype(&udev_unref)> udev(udev_new(), &udev_unref);
     if (!udev) {
@@ -44,7 +46,11 @@
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
