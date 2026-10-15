$NetBSD$

Port joystick and gamepad handling to SDL3 instance IDs and APIs.
Keep compact button rows, safe device lifetime, and current enum names.

--- kcms/gamecontroller/device.cpp.orig
+++ kcms/gamecontroller/device.cpp
@@ -8,7 +8,7 @@
 
 #include <KLocalizedString>
 
-#include <SDL2/SDL_hidapi.h>
+#include <SDL3/SDL_hidapi.h>
 
 #include "logging.h"
 #include "udevmatcher.h"
@@ -25,25 +25,24 @@
                                          i18n("Arcade Pad"),
                                          i18n("Throttle")};
 
-// NOTE: Keep in sync with SDL_gamecontrollertype from SDL_gamecontroller.h
+// NOTE: Keep in sync with SDL_GamepadType from SDL_gamepad.h
 static QStringList kControllerTypeNames = {
     i18n("Unknown"),
+    i18n("Standard gamepad"),
     i18n("XBox 360"),
     i18n("XBox One"),
     i18n("Sony Dualshock 3"),
     i18n("Sony Dualshock 4"),
-    i18n("Switch Pro"),
-    i18n("Virtual"),
     i18n("Sony Dualsense"),
-    i18n("Amazon Luna"),
-    i18n("Google Stadia"),
-    i18n("NVidia Shield"),
+    i18n("Switch Pro"),
     i18n("Switch Left Joy-Con"),
     i18n("Switch Right Joy-Con"),
     i18n("Switch Paired Joy-Con"),
+    i18n("Nintendo GameCube"),
+    i18n("Steam Controller"),
 };
 
-// NOTE: Keep in sync with SDL_GameControllerButton from SDL_gamecontroller.h
+// NOTE: Keep in sync with SDL_GamepadButton from SDL_gamepad.h
 static QStringList kButtonNames = {
     i18nc("The game controller button with a letter A on it", "A button"),
     i18nc("The game controller button with a letter B on it", "B button"),
@@ -67,6 +66,11 @@
     i18nc("The game controller's 3rd paddle button", "Paddle button 3"), /* Xbox Elite paddle P2 (lower left, facing the back) */
     i18nc("The game controller's 4th paddle button", "Paddle button 4"), /* Xbox Elite paddle P4 (lower right, facing the back) */
     i18nc("The button under the game controller's touchpad", "Touchpad button"), /* PS4/PS5 touchpad button */
+    i18nc("The game controller's 2nd miscellaneous button", "Miscellaneous button 2"),
+    i18nc("The game controller's 3rd miscellaneous button", "Miscellaneous button 3"),
+    i18nc("The game controller's 4th miscellaneous button", "Miscellaneous button 4"),
+    i18nc("The game controller's 5th miscellaneous button", "Miscellaneous button 5"),
+    i18nc("The game controller's 6th miscellaneous button", "Miscellaneous button 6"),
 };
 
 static QStringList kConnectionTypeString = {
@@ -75,9 +79,9 @@
     i18nc("Bluetooth connected controller", "Bluetooth"),
 };
 
-QString ButtonToButtonName(SDL_GameControllerButton button)
+QString ButtonToButtonName(SDL_GamepadButton button)
 {
-    if (button > SDL_CONTROLLER_BUTTON_INVALID && button < SDL_CONTROLLER_BUTTON_MAX) {
+    if (button > SDL_GAMEPAD_BUTTON_INVALID && button < kButtonNames.size()) {
         return kButtonNames.at(button);
     } else {
         return i18n("Invalid button value");
@@ -87,13 +91,18 @@
 // Get the SDL hid info for the joystick with the given vendor, and product
 SDL_hid_device_info getJoystickHidInfo(short vendor, short product, std::string path)
 {
+    SDL_hid_device_info result{};
+    result.interface_number = -2;
+    if (path.empty()) {
+        return result;
+    }
+
     SDL_hid_device_info *info = SDL_hid_enumerate(vendor, product);
 
     SDL_hid_device_info *current = info;
 
     qCDebug(KCM_GAMECONTROLLER) << "Checking for hidapi with vendor: " << vendor << " and product: " << product;
 
-    SDL_hid_device_info result;
     if (info) {
         if (!info->next) {
             // We found our device, so copy the data we are interested in.
@@ -116,7 +125,7 @@
                 auto test_id = UDevMatcher::deviceToUdevId(current->path);
                 qCDebug(KCM_GAMECONTROLLER) << "Found device: " << current->path << " udev id: " << test_id;
 
-                if (to_match == test_id) {
+                if (!to_match.empty() && to_match == test_id) {
                     result.interface_number = current->interface_number;
 
                     qCDebug(KCM_GAMECONTROLLER) << "Found hidapi data for path " << current->path;
@@ -134,9 +143,9 @@
     return result;
 }
 
-Device::Device(int deviceIndex, QObject *parent)
+Device::Device(SDL_JoystickID deviceId, QObject *parent)
     : QObject(parent)
-    , m_deviceIndex(deviceIndex)
+    , m_deviceId(deviceId)
     , m_connectionType(UnknownType)
 {
 }
@@ -151,17 +160,17 @@
         return true;
     }
 
-    m_joystick = SDL_JoystickOpen(m_deviceIndex);
-    if (!m_joystick) {
-        qCWarning(KCM_GAMECONTROLLER) << "Failed to load joystick at: " << m_deviceIndex;
-        return false;
-    }
+    m_joystick = SDL_OpenJoystick(m_deviceId);
+    if (!m_joystick) {
+        qCWarning(KCM_GAMECONTROLLER) << "Failed to load joystick at: " << m_deviceId;
+        return false;
+    }
 
-    short vendor = SDL_JoystickGetVendor(m_joystick);
-    short product = SDL_JoystickGetProduct(m_joystick);
-    auto path = SDL_JoystickPath(m_joystick);
+    short vendor = SDL_GetJoystickVendor(m_joystick);
+    short product = SDL_GetJoystickProduct(m_joystick);
+    auto path = SDL_GetJoystickPath(m_joystick);
     qCDebug(KCM_GAMECONTROLLER) << "Device path: " << path;
-    SDL_hid_device_info info = getJoystickHidInfo(vendor, product, path);
+    SDL_hid_device_info info = getJoystickHidInfo(vendor, product, path ? path : "");
     if (info.interface_number == -2) {
         // Couldn't find hidapi device, so unknown
         m_connectionType = UnknownType;
@@ -168,20 +180,22 @@
         m_connectionType = USBType;
     }
 
-    m_controller = SDL_GameControllerOpen(m_deviceIndex);
+    m_buttonType.clear();
+    m_buttonCount = 0;
+    m_controller = SDL_IsGamepad(m_deviceId) ? SDL_OpenGamepad(m_deviceId) : nullptr;
     if (!m_controller) {
-        m_leftTrigger = SDL_JoystickGetAxis(m_joystick, SDL_CONTROLLER_AXIS_TRIGGERLEFT);
-        m_rightTrigger = SDL_JoystickGetAxis(m_joystick, SDL_CONTROLLER_AXIS_TRIGGERRIGHT);
-        qCDebug(KCM_GAMECONTROLLER) << "Device" << m_deviceIndex << "is not a gamepad. using as joystick";
-        m_buttonCount = SDL_JoystickNumButtons(m_joystick);
+        m_leftTrigger = SDL_GetJoystickAxis(m_joystick, SDL_GAMEPAD_AXIS_LEFT_TRIGGER) / static_cast<float>(std::numeric_limits<Sint16>::max());
+        m_rightTrigger = SDL_GetJoystickAxis(m_joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER) / static_cast<float>(std::numeric_limits<Sint16>::max());
+        qCDebug(KCM_GAMECONTROLLER) << "Device" << m_deviceId << "is not a gamepad. using as joystick";
+        m_buttonCount = SDL_GetNumJoystickButtons(m_joystick);
     } else {
-        m_leftTrigger = SDL_GameControllerGetAxis(m_controller, SDL_CONTROLLER_AXIS_TRIGGERLEFT);
-        m_rightTrigger = SDL_GameControllerGetAxis(m_controller, SDL_CONTROLLER_AXIS_TRIGGERRIGHT);
+        m_leftTrigger = SDL_GetGamepadAxis(m_controller, SDL_GAMEPAD_AXIS_LEFT_TRIGGER) / static_cast<float>(std::numeric_limits<Sint16>::max());
+        m_rightTrigger = SDL_GetGamepadAxis(m_controller, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER) / static_cast<float>(std::numeric_limits<Sint16>::max());
 
         // We have a controller, so check which buttons we have
-        for (int i = 0; i < SDL_CONTROLLER_BUTTON_MAX; ++i) {
+        for (int i = 0; i < SDL_GAMEPAD_BUTTON_COUNT; ++i) {
             // If we have this button type, add it to our map and increase count.
-            if (SDL_GameControllerHasButton(m_controller, static_cast<SDL_GameControllerButton>(i))) {
+            if (SDL_GamepadHasButton(m_controller, static_cast<SDL_GamepadButton>(i))) {
                 m_buttonType[m_buttonCount] = i;
                 m_buttonCount++;
             }
@@ -197,12 +211,14 @@
     }
 
     if (m_controller) {
-        SDL_GameControllerClose(m_controller);
+        SDL_CloseGamepad(m_controller);
         m_controller = nullptr;
     }
 
-    SDL_JoystickClose(m_joystick);
+    SDL_CloseJoystick(m_joystick);
     m_joystick = nullptr;
+    m_buttonType.clear();
+    m_buttonCount = 0;
 }
 
 bool Device::isController() const
@@ -212,37 +228,37 @@
 
 SDL_JoystickID Device::id() const
 {
-    return SDL_JoystickInstanceID(m_joystick);
+    return SDL_GetJoystickID(m_joystick);
 }
 
 QString Device::name() const
 {
-    return QString::fromLocal8Bit(SDL_JoystickName(m_joystick));
+    return QString::fromLocal8Bit(SDL_GetJoystickName(m_joystick));
 }
 
 QString Device::path() const
 {
-    return QString::fromLocal8Bit(SDL_JoystickPath(m_joystick));
+    return QString::fromLocal8Bit(SDL_GetJoystickPath(m_joystick));
 }
 
 QString Device::type() const
 {
-    return kJoystickTypeNames.at(SDL_JoystickGetType(m_joystick));
+    return kJoystickTypeNames.value(SDL_GetJoystickType(m_joystick), i18n("Unknown"));
 }
 
-SDL_GameControllerType Device::controllerType() const
+SDL_GamepadType Device::controllerType() const
 {
     if (m_controller) {
-        return SDL_GameControllerGetType(m_controller);
+        return SDL_GetGamepadType(m_controller);
     }
-    return SDL_CONTROLLER_TYPE_UNKNOWN;
+    return SDL_GAMEPAD_TYPE_UNKNOWN;
 
 }
 
 QString Device::controllerTypeName() const
 {
     if (m_controller) {
-        return kControllerTypeNames.at(SDL_GameControllerGetType(m_controller));
+        return kControllerTypeNames.value(SDL_GetGamepadType(m_controller), i18n("Unknown"));
     } else {
         return i18n("Not a controller");
     }
@@ -255,7 +271,7 @@
 
 bool Device::isVirtual() const
 {
-    return SDL_JoystickIsVirtual(m_deviceIndex);
+    return SDL_IsJoystickVirtual(m_deviceId);
 }
 
 int Device::buttonCount() const
@@ -266,27 +282,30 @@
 bool Device::buttonState(int index) const
 {
     // Invalid index
-    if (index < 0 || index > m_buttonCount)
+    if (index < 0 || index >= m_buttonCount)
         return false;
 
     // If we are a game controller, use that api to get button state
     if (m_controller) {
-        return SDL_GameControllerGetButton(m_controller, static_cast<SDL_GameControllerButton>(m_buttonType.value(index))) != 0;
+        return SDL_GetGamepadButton(m_controller, static_cast<SDL_GamepadButton>(m_buttonType.value(index))) != 0;
     }
-    return SDL_JoystickGetButton(m_joystick, index) != 0;
+    return SDL_GetJoystickButton(m_joystick, index) != 0;
 }
 
 QString Device::buttonName(int index) const
 {
+    if (index < 0 || index >= m_buttonCount) {
+        return i18n("Invalid button value");
+    }
     if (m_controller) {
-        return ButtonToButtonName(static_cast<SDL_GameControllerButton>(m_buttonType.value(index)));
+        return ButtonToButtonName(static_cast<SDL_GamepadButton>(m_buttonType.value(index)));
     }
     return QString::number(index + 1);
 }
 
 int Device::axisCount() const
 {
-    return SDL_JoystickNumAxes(m_joystick);
+    return SDL_GetNumJoystickAxes(m_joystick);
 }
 
 QVector2D Device::leftAxisValue() const
@@ -311,12 +330,12 @@
 
 int Device::hatCount() const
 {
-    return SDL_JoystickNumHats(m_joystick);
+    return SDL_GetNumJoystickHats(m_joystick);
 }
 
 QVector2D Device::hatPosition(int index) const
 {
-    const Uint8 hat = SDL_JoystickGetHat(m_joystick, index);
+    const Uint8 hat = SDL_GetJoystickHat(m_joystick, index);
     QVector2D position;
 
     if ((hat & SDL_HAT_LEFT) != 0) {
@@ -339,55 +358,59 @@
     Q_EMIT buttonStateChanged(event.button);
 }
 
-void Device::onControllerButtonEvent(const SDL_ControllerButtonEvent &event)
+void Device::onControllerButtonEvent(const SDL_GamepadButtonEvent &event)
 {
-    qCDebug(KCM_GAMECONTROLLER) << "Got controller button event for button: " << ButtonToButtonName(SDL_GameControllerButton(event.button));
-    Q_EMIT buttonStateChanged(event.button);
+    qCDebug(KCM_GAMECONTROLLER) << "Got controller button event for button: " << ButtonToButtonName(SDL_GamepadButton(event.button));
+    // SDL reports a button enum. The view uses the compact row map.
+    const int index = m_buttonType.key(event.button, -1);
+    if (index >= 0) {
+        Q_EMIT buttonStateChanged(index);
+    }
 }
 
 void Device::onAxisEvent(const SDL_JoyAxisEvent &event)
 {
     const float value = static_cast<float>(event.value) / std::numeric_limits<Sint16>::max();
-    if (event.axis == SDL_CONTROLLER_AXIS_LEFTX) {
+    if (event.axis == SDL_GAMEPAD_AXIS_LEFTX) {
         m_leftAxis.setX(value);
         Q_EMIT leftAxisChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_LEFTY) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_LEFTY) {
         m_leftAxis.setY(value);
         Q_EMIT leftAxisChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_RIGHTX) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_RIGHTX) {
         m_rightAxis.setX(value);
         Q_EMIT rightAxisChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_RIGHTY) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_RIGHTY) {
         m_rightAxis.setY(value);
         Q_EMIT rightAxisChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_TRIGGERLEFT) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_LEFT_TRIGGER) {
         m_leftTrigger = value;
         Q_EMIT leftTriggerChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_TRIGGERRIGHT) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_RIGHT_TRIGGER) {
         m_rightTrigger = value;
         Q_EMIT rightTriggerChanged();
     }
 }
 
-void Device::onControllerAxisEvent(const SDL_ControllerAxisEvent &event)
+void Device::onControllerAxisEvent(const SDL_GamepadAxisEvent &event)
 {
     const float value = static_cast<float>(event.value) / std::numeric_limits<Sint16>::max();
-    if (event.axis == SDL_CONTROLLER_AXIS_LEFTX) {
+    if (event.axis == SDL_GAMEPAD_AXIS_LEFTX) {
         m_leftAxis.setX(value);
         Q_EMIT leftAxisChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_LEFTY) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_LEFTY) {
         m_leftAxis.setY(value);
         Q_EMIT leftAxisChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_RIGHTX) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_RIGHTX) {
         m_rightAxis.setX(value);
         Q_EMIT rightAxisChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_RIGHTY) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_RIGHTY) {
         m_rightAxis.setY(value);
         Q_EMIT rightAxisChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_TRIGGERLEFT) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_LEFT_TRIGGER) {
         m_leftTrigger = value;
         Q_EMIT leftTriggerChanged();
-    } else if (event.axis == SDL_CONTROLLER_AXIS_TRIGGERRIGHT) {
+    } else if (event.axis == SDL_GAMEPAD_AXIS_RIGHT_TRIGGER) {
         m_rightTrigger = value;
         Q_EMIT rightTriggerChanged();
     }
