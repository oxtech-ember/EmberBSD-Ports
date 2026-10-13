// SPDX-License-Identifier: GPL-2.0-or-later
// Test the actual Plasma device implementation with SDL virtual devices.
#include "device.h"
#include "devicemodel.h"
#include "udevmatcher.h"
#include <SDL3/SDL.h>
#include <QSignalSpy>
#include <QTest>
#include <limits>

QString ButtonToButtonName(SDL_GamepadButton button);

class VirtualJoystick
{
public:
    explicit VirtualJoystick(SDL_JoystickType type)
    {
        SDL_VirtualJoystickDesc desc;
        SDL_INIT_INTERFACE(&desc);
        desc.type = type;
        desc.naxes = SDL_GAMEPAD_AXIS_COUNT;
        desc.nbuttons = 2;
        desc.nhats = 1;
        desc.name = "Plasma SDL3 test";
        desc.button_mask = (1U << SDL_GAMEPAD_BUTTON_SOUTH) | (1U << SDL_GAMEPAD_BUTTON_MISC6);
        desc.axis_mask = (1U << SDL_GAMEPAD_AXIS_COUNT) - 1;
        id = SDL_AttachVirtualJoystick(&desc);
    }
    ~VirtualJoystick() { if (id) SDL_DetachVirtualJoystick(id); }
    SDL_JoystickID id = 0;
};

class DeviceTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void initTestCase()
    {
        SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
        QVERIFY2(SDL_InitSubSystem(SDL_INIT_GAMEPAD), SDL_GetError());
    }
    void init() { SDL_FlushEvents(SDL_EVENT_FIRST, SDL_EVENT_LAST); }
    void cleanupTestCase() { SDL_QuitSubSystem(SDL_INIT_GAMEPAD); }
    void invalidDevice()
    {
        Device device(0);
        QVERIFY(!device.open());
        device.close();
        QVERIFY(!device.buttonState(0));
        QCOMPARE(device.leftTriggerValue(), 0.0F);
        QCOMPARE(device.rightTriggerValue(), 0.0F);
        QVERIFY(UDevMatcher::deviceToUdevId("").empty());
        QVERIFY(UDevMatcher::deviceToUdevId("/dev/uhid0").empty());
    }
    void joystickInstanceIdAndState()
    {
        VirtualJoystick first(SDL_JOYSTICK_TYPE_WHEEL);
        VirtualJoystick second(SDL_JOYSTICK_TYPE_WHEEL);
        QVERIFY(first.id && second.id && first.id != second.id);
        Device device(second.id);
        QVERIFY2(device.open(), SDL_GetError());
        QCOMPARE(device.id(), second.id);
        QVERIFY(device.isVirtual());
        QVERIFY(!device.isController());
        QCOMPARE(device.buttonCount(), 2);
        auto *joystick = SDL_GetJoystickFromID(second.id);
        QVERIFY(joystick);
        QVERIFY(SDL_SetJoystickVirtualButton(joystick, 1, true));
        QVERIFY(SDL_SetJoystickVirtualHat(joystick, 0, SDL_HAT_RIGHTUP));
        SDL_UpdateJoysticks();
        QVERIFY(device.buttonState(1));
        QVERIFY(!device.buttonState(-1));
        QVERIFY(!device.buttonState(2));
        QCOMPARE(device.hatPosition(0), QVector2D(32767, -32768));
        device.close();
        QVERIFY(device.open());
        QCOMPARE(device.buttonCount(), 2);
    }
    void mappedButtonsAndReopen()
    {
        VirtualJoystick joystick(SDL_JOYSTICK_TYPE_GAMEPAD);
        QVERIFY(joystick.id);
        Device device(joystick.id);
        QVERIFY2(device.open(), SDL_GetError());
        QVERIFY(device.isController());
        QCOMPARE(device.controllerType(), SDL_GAMEPAD_TYPE_STANDARD);
        QCOMPARE(device.controllerTypeName(), QStringLiteral("Standard gamepad"));
        QCOMPARE(device.buttonCount(), 2);
        QCOMPARE(device.m_buttonType.value(1), int(SDL_GAMEPAD_BUTTON_MISC6));
        QVERIFY(!device.buttonName(1).isEmpty());
        for (int i = 0; i < SDL_GAMEPAD_BUTTON_COUNT; ++i) {
            QVERIFY(!ButtonToButtonName(static_cast<SDL_GamepadButton>(i)).isEmpty());
        }
        auto *handle = SDL_GetJoystickFromID(joystick.id);
        QVERIFY(SDL_SetJoystickVirtualButton(handle, 0, true));
        SDL_UpdateJoysticks();
        QVERIFY(device.buttonState(0));
        // The old inclusive upper bound incorrectly read button zero here.
        QVERIFY(!device.buttonState(device.buttonCount()));
        QSignalSpy spy(&device, &Device::buttonStateChanged);
        SDL_GamepadButtonEvent button{};
        button.which = joystick.id;
        button.button = SDL_GAMEPAD_BUTTON_MISC6;
        device.onControllerButtonEvent(button);
        QCOMPARE(spy.size(), 1);
        QCOMPARE(spy.takeFirst().at(0).toInt(), 1);
        button.button = SDL_GAMEPAD_BUTTON_EAST;
        device.onControllerButtonEvent(button);
        QCOMPARE(spy.size(), 0);
        device.close();
        QVERIFY(device.open());
        QCOMPARE(device.buttonCount(), 2);
    }
    void axisEvents()
    {
        VirtualJoystick joystick(SDL_JOYSTICK_TYPE_GAMEPAD);
        Device device(joystick.id);
        QVERIFY(device.open());
        QSignalSpy left(&device, &Device::leftAxisChanged);
        QSignalSpy trigger(&device, &Device::rightTriggerChanged);
        SDL_GamepadAxisEvent axis{};
        axis.axis = SDL_GAMEPAD_AXIS_LEFTX;
        axis.value = 16384;
        device.onControllerAxisEvent(axis);
        QCOMPARE(left.size(), 1);
        QCOMPARE(device.leftAxisValue().x(), 16384.0F / 32767.0F);
        axis.axis = SDL_GAMEPAD_AXIS_RIGHT_TRIGGER;
        axis.value = 32767;
        device.onControllerAxisEvent(axis);
        QCOMPARE(trigger.size(), 1);
        QCOMPARE(device.rightTriggerValue(), 1.0F);
    }
    void modelDispatchAndDetach()
    {
        VirtualJoystick joystick(SDL_JOYSTICK_TYPE_GAMEPAD);
        QVERIFY(joystick.id);
        DeviceModel model;
        model.poll();
        QVERIFY(!model.device(joystick.id));
        // Admit this virtual fixture only inside the test. Production policy
        // still rejects virtual devices. The event dispatch code is unchanged.
        auto *device = new Device(joystick.id, &model);
        QVERIFY(device->open());
        model.m_devices.insert(joystick.id, device);
        QSignalSpy button(device, &Device::buttonStateChanged);
        QSignalSpy axis(device, &Device::leftAxisChanged);
        auto *handle = SDL_GetJoystickFromID(joystick.id);
        QVERIFY(SDL_SetJoystickVirtualButton(handle, 1, true));
        QVERIFY(SDL_SetJoystickVirtualAxis(handle, SDL_GAMEPAD_AXIS_LEFTX, 16384));
        SDL_UpdateJoysticks();
        model.poll();
        QVERIFY(!button.isEmpty());
        QCOMPARE(button.last().at(0).toInt(), 1);
        QVERIFY(!axis.isEmpty());
        QVERIFY(device->buttonState(1));
        QCOMPARE(device->leftAxisValue().x(), 16384.0F / 32767.0F);
        const auto id = joystick.id;
        QVERIFY(SDL_DetachVirtualJoystick(id));
        joystick.id = 0;
        model.poll();
        QVERIFY(!model.device(id));
        QVERIFY(!device->m_joystick);
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
    }
    void modelLifecycle()

    {
        VirtualJoystick joystick(SDL_JOYSTICK_TYPE_GAMEPAD);
        {
            DeviceModel model;
            model.poll();
            // The production model intentionally excludes virtual controllers.
            QVERIFY(!model.device(joystick.id));
            const int count = model.count();
            model.addDevice(joystick.id);
            QCOMPARE(model.count(), count);
            model.removeDevice(joystick.id);
            QCOMPARE(model.count(), count);
        }
        // Model shutdown must not destroy another SDL subsystem owner's lease.
        QVERIFY(SDL_WasInit(SDL_INIT_GAMEPAD) & SDL_INIT_GAMEPAD);
        Device device(joystick.id);
        QVERIFY(device.open());
    }
};
QTEST_GUILESS_MAIN(DeviceTest)
#include "device-test.moc"
