$NetBSD$

Port joystick and gamepad handling to SDL3 instance IDs and APIs.
Keep compact button rows, safe device lifetime, and current enum names.

--- kcms/gamecontroller/devicemodel.h.orig
+++ kcms/gamecontroller/devicemodel.h
@@ -13,7 +13,7 @@
 #include <QPointer>
 #include <QQmlEngine>
 
-#include <SDL2/SDL_joystick.h>
+#include <SDL3/SDL_joystick.h>
 
 #include "device.h"
 
@@ -56,11 +56,12 @@
     void poll();
 
 private:
+    friend class DeviceTest;
     DeviceModel();
-    void addDevice(const int deviceIndex);
+    void addDevice(SDL_JoystickID deviceId);
     void removeDevice(const SDL_JoystickID id);
 
-    // Map of sdl indexes to Gamepad devices
+    // Map of SDL instance IDs to Gamepad devices
     QMap<SDL_JoystickID, Device *> m_devices;
     QPointer<QTimer> m_timer;
 };
