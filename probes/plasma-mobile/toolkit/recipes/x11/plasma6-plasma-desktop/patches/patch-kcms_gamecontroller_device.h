$NetBSD$

Port joystick and gamepad handling to SDL3 instance IDs and APIs.
Keep compact button rows, safe device lifetime, and current enum names.

--- kcms/gamecontroller/device.h.orig
+++ kcms/gamecontroller/device.h
@@ -11,16 +11,16 @@
 #include <QVector2D>
 #include <QVector>
 
-#include <SDL2/SDL_events.h>
-#include <SDL2/SDL_gamecontroller.h>
-#include <SDL2/SDL_joystick.h>
+#include <SDL3/SDL_events.h>
+#include <SDL3/SDL_gamepad.h>
+#include <SDL3/SDL_joystick.h>
 
 class Device : public QObject
 {
     Q_OBJECT
 
     Q_PROPERTY(QString type READ type CONSTANT)
-    Q_PROPERTY(SDL_GameControllerType controllerType READ controllerType CONSTANT)
+    Q_PROPERTY(SDL_GamepadType controllerType READ controllerType CONSTANT)
     Q_PROPERTY(QString controllerTypeName READ controllerTypeName CONSTANT)
     Q_PROPERTY(QString connectionType READ connectionType CONSTANT)
     Q_PROPERTY(QVector2D leftAxis READ leftAxisValue NOTIFY leftAxisChanged)
@@ -29,7 +29,7 @@
     Q_PROPERTY(float rightTrigger READ rightTriggerValue NOTIFY rightTriggerChanged)
 
 public:
-    Device(int deviceIndex, QObject *parent = nullptr);
+    Device(SDL_JoystickID deviceId, QObject *parent = nullptr);
     ~Device();
 
     enum ConnectionType {
@@ -50,7 +50,7 @@
     // Joystick type, wheel, controller, etc.
     QString type() const;
     // Gamecontroller type
-    SDL_GameControllerType controllerType() const;
+    SDL_GamepadType controllerType() const;
     // Gamecontroller type name, switch pro, ps5, etc.
     QString controllerTypeName() const;
     // Unknown, USB, Bluetooth
@@ -84,23 +84,24 @@
     void connectionTypeChanged();
 
 private:
+    friend class DeviceTest;
     friend class DeviceModel;
 
     void onButtonEvent(const SDL_JoyButtonEvent &event);
     void onAxisEvent(const SDL_JoyAxisEvent &event);
     void onHatEvent(const SDL_JoyHatEvent &event);
-    // The same as above but using SDL_Controller*Event types
-    void onControllerButtonEvent(const SDL_ControllerButtonEvent &event);
-    void onControllerAxisEvent(const SDL_ControllerAxisEvent &event);
+    // The same as above but using SDL_Gamepad*Event types
+    void onControllerButtonEvent(const SDL_GamepadButtonEvent &event);
+    void onControllerAxisEvent(const SDL_GamepadAxisEvent &event);
 
-    int m_deviceIndex = -1;
+    SDL_JoystickID m_deviceId = 0;
     QVector2D m_leftAxis;
     QVector2D m_rightAxis;
-    float m_leftTrigger;
-    float m_rightTrigger;
+    float m_leftTrigger = 0;
+    float m_rightTrigger = 0;
     SDL_Joystick *m_joystick = nullptr;
-    SDL_GameController *m_controller = nullptr;
-    // Map of index to SDL_CONTROLLER button type for all buttons this gamecontroller has
+    SDL_Gamepad *m_controller = nullptr;
+    // Map of index to SDL_GAMEPAD button type for all buttons this gamecontroller has
     QMap<int, int> m_buttonType;
     int m_buttonCount = 0;
     ConnectionType m_connectionType = UnknownType;
