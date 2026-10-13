$NetBSD$

Port joystick and gamepad handling to SDL3 instance IDs and APIs.
Keep compact button rows, safe device lifetime, and current enum names.

--- kcms/gamecontroller/devicemodel.cpp.orig
+++ kcms/gamecontroller/devicemodel.cpp
@@ -11,7 +11,7 @@
 #include <KLocalizedString>
 #include <QTimer>
 
-#include <SDL2/SDL.h>
+#include <SDL3/SDL.h>
 
 #include "logging.h"
 
@@ -37,9 +37,9 @@
 DeviceModel::~DeviceModel()
 {
     if (initialized) {
-        qCDebug(KCM_GAMECONTROLLER) << "Calling SDL_Quit";
+        qCDebug(KCM_GAMECONTROLLER) << "Calling SDL_QuitSubSystem";
         qDeleteAll(m_devices);
-        SDL_Quit();
+        SDL_QuitSubSystem(SDL_INIT_GAMEPAD);
         initialized = false;
     }
 }
@@ -81,9 +81,9 @@
 void DeviceModel::poll()
 {
     if (!initialized) {
-        qCDebug(KCM_GAMECONTROLLER) << "Calling SDL_Init";
+        qCDebug(KCM_GAMECONTROLLER) << "Calling SDL_InitSubSystem";
         SDL_SetHint(SDL_HINT_NO_SIGNAL_HANDLERS, "1");
-        if (SDL_Init(SDL_INIT_GAMECONTROLLER) != 0) {
+        if (!SDL_InitSubSystem(SDL_INIT_GAMEPAD)) {
             qCWarning(KCM_GAMECONTROLLER) << "Could not initialise SDL. No controllers will be shown: " << qPrintable(SDL_GetError());
             return;
         }
@@ -93,49 +93,49 @@
     SDL_Event event{};
     while (SDL_PollEvent(&event)) {
         switch (event.type) {
-        case SDL_JOYDEVICEADDED:
+        case SDL_EVENT_JOYSTICK_ADDED:
             addDevice(event.jdevice.which);
             break;
-        case SDL_JOYDEVICEREMOVED:
+        case SDL_EVENT_JOYSTICK_REMOVED:
             removeDevice(event.jdevice.which);
             break;
-        case SDL_JOYBUTTONDOWN:
-        case SDL_JOYBUTTONUP:
-            if (m_devices.contains(event.jbutton.which) && !m_devices.value(event.jaxis.which)->isController()) {
+        case SDL_EVENT_JOYSTICK_BUTTON_DOWN:
+        case SDL_EVENT_JOYSTICK_BUTTON_UP:
+            if (m_devices.contains(event.jbutton.which) && !m_devices.value(event.jbutton.which)->isController()) {
                 m_devices.value(event.jbutton.which)->onButtonEvent(event.jbutton);
             }
             break;
-        case SDL_JOYAXISMOTION:
+        case SDL_EVENT_JOYSTICK_AXIS_MOTION:
             if (m_devices.contains(event.jaxis.which) && !m_devices.value(event.jaxis.which)->isController()) {
                 m_devices.value(event.jaxis.which)->onAxisEvent(event.jaxis);
             }
             break;
-        case SDL_JOYHATMOTION:
+        case SDL_EVENT_JOYSTICK_HAT_MOTION:
             if (m_devices.contains(event.jhat.which)) {
                 m_devices.value(event.jhat.which)->onHatEvent(event.jhat);
             }
             break;
-        case SDL_CONTROLLERBUTTONDOWN:
-        case SDL_CONTROLLERBUTTONUP:
-            if (m_devices.contains(event.cbutton.which) && m_devices.value(event.cbutton.which)->isController()) {
-                m_devices.value(event.cbutton.which)->onControllerButtonEvent(event.cbutton);
+        case SDL_EVENT_GAMEPAD_BUTTON_DOWN:
+        case SDL_EVENT_GAMEPAD_BUTTON_UP:
+            if (m_devices.contains(event.gbutton.which) && m_devices.value(event.gbutton.which)->isController()) {
+                m_devices.value(event.gbutton.which)->onControllerButtonEvent(event.gbutton);
             }
             break;
-        case SDL_CONTROLLERAXISMOTION:
-            if (m_devices.contains(event.caxis.which) && m_devices.value(event.caxis.which)->isController()) {
-                m_devices.value(event.caxis.which)->onControllerAxisEvent(event.caxis);
+        case SDL_EVENT_GAMEPAD_AXIS_MOTION:
+            if (m_devices.contains(event.gaxis.which) && m_devices.value(event.gaxis.which)->isController()) {
+                m_devices.value(event.gaxis.which)->onControllerAxisEvent(event.gaxis);
             }
             break;
         }
     }
 }
 
-void DeviceModel::addDevice(const int deviceIndex)
+void DeviceModel::addDevice(SDL_JoystickID deviceId)
 {
-    auto device = std::make_unique<Device>(deviceIndex, this);
+    auto device = std::make_unique<Device>(deviceId, this);
     if (!device->open()) {
         const QString error = QString::fromLocal8Bit(SDL_GetError());
-        qCCritical(KCM_GAMECONTROLLER).nospace() << "Could not open device " << deviceIndex << ": " << error;
+        qCCritical(KCM_GAMECONTROLLER).nospace() << "Could not open device " << deviceId << ": " << error;
         return;
     }
 
@@ -146,11 +146,11 @@
     }
 
     if (device->isVirtual()) {
-        qCWarning(KCM_GAMECONTROLLER) << "Skipping device" << deviceIndex << "since it is virtual";
+        qCWarning(KCM_GAMECONTROLLER) << "Skipping device" << deviceId << "since it is virtual";
         return;
     }
 
-    qCDebug(KCM_GAMECONTROLLER) << "Adding device" << deviceIndex << "with ID" << id;
+    qCDebug(KCM_GAMECONTROLLER) << "Adding device" << deviceId << "with ID" << id;
 
     beginInsertRows(QModelIndex(), m_devices.count(), m_devices.count());
     m_devices.insert(id, device.release());
@@ -173,6 +173,7 @@
     qCDebug(KCM_GAMECONTROLLER) << "Removing device with ID" << id;
 
     beginRemoveRows(QModelIndex(), index, index);
+    m_devices.value(id)->close();
     m_devices.value(id)->deleteLater();
     m_devices.remove(id);
     endRemoveRows();
