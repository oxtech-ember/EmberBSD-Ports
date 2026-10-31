// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).

#include "qbsdfblayout_p.h"
#include "qbsdfbpointer_p.h"

#include <array>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>

namespace {

using Input = QBsdFb::PointerInput;
using EventKind = Input::EventKind;
using Event = Input::Output;
using EventType = Input::Kind;
using AxisRange = Input::AxisRange;
using QBsdFb::FrameInfo;
using QBsdFb::Layout;
using QBsdFb::Point;
using QBsdFb::Rotation;

int failures = 0;

void check(bool condition, const char *name)
{
    if (!condition) {
        std::cerr << "FAIL: " << name << '\n';
        ++failures;
    }
}

bool same(Point a, Point b)
{
    return a.x == b.x && a.y == b.y;
}

bool same(const Event &event, EventType type, Point position,
          std::uint32_t button, std::uint32_t buttons)
{
    return event.kind == type && same(event.position, position)
        && event.button == button && event.buttons == buttons;
}

Layout testLayout()
{
    FrameInfo info{};
    info.fbsize = 4096000;
    info.offset = 256;
    info.width = 800;
    info.height = 1280;
    info.stride = 3200;
    info.bpp = 32;
    info.pixelType = 0;
    info.flags = 1;
    info.redOffset = 16;
    info.redSize = 8;
    info.greenOffset = 8;
    info.greenSize = 8;
    info.blueOffset = 0;
    info.blueSize = 8;
    info.alphaSize = 0;
    Layout layout{};
    check(QBsdFb::makeLayout(info, layout), "pointer fixture layout is valid");
    return layout;
}

void feed(Input &input, EventKind kind, int value, std::vector<Event> &events)
{
    input.feed(kind, value, [&](const Event &event) { events.push_back(event); });
}

void drain(Input &input, std::vector<Event> &events)
{
    input.drain([&](const Event &event) { events.push_back(event); });
}

void disconnect(Input &input, std::vector<Event> &events)
{
    input.disconnect([&](const Event &event) { events.push_back(event); });
}

void testRotationCorners(const Layout &layout)
{
    struct CornerCase {
        Rotation rotation = Rotation::R0;
        std::array<Point, 4> native{};
        std::array<Point, 4> logical{};
    };
    const std::array cases{
        CornerCase{Rotation::R0,
                   {{{0, 0}, {799, 0}, {0, 1279}, {799, 1279}}},
                   {{{0, 0}, {799, 0}, {0, 1279}, {799, 1279}}}},
        CornerCase{Rotation::R90,
                   {{{0, 0}, {799, 0}, {0, 1279}, {799, 1279}}},
                   {{{0, 799}, {0, 0}, {1279, 799}, {1279, 0}}}},
        CornerCase{Rotation::R180,
                   {{{0, 0}, {799, 0}, {0, 1279}, {799, 1279}}},
                   {{{799, 1279}, {0, 1279}, {799, 0}, {0, 0}}}},
        CornerCase{Rotation::R270,
                   {{{0, 0}, {799, 0}, {0, 1279}, {799, 1279}}},
                   {{{1279, 0}, {1279, 799}, {0, 0}, {0, 799}}}},
    };

    const AxisRange axes{0, 799, 0, 1279};
    for (const CornerCase &test : cases) {
        for (std::size_t i = 0; i < test.native.size(); ++i) {
            Input input(layout, test.rotation, axes);
            std::vector<Event> events;
            feed(input, EventKind::AbsoluteX, test.native[i].x, events);
            feed(input, EventKind::AbsoluteY, test.native[i].y, events);
            drain(input, events);
            feed(input, EventKind::ButtonDown, 0, events);
            check(!events.empty()
                      && same(events.back(), EventType::Press, test.logical[i], 1U, 1U),
                  "raw axis corner maps to independently specified logical corner");
        }
    }
}

void testInitialPressAndAxisDrain(const Layout &layout)
{
    Input input(layout, Rotation::R0, AxisRange{0, 799, 0, 1279});
    std::vector<Event> events;
    check(input.valid(), "valid layout and ranges enable pointer input");

    feed(input, EventKind::ButtonDown, 0, events);
    check(events.size() == 1
              && same(events[0], EventType::Press, {0, 0}, 1U, 1U),
          "initial button press uses zero-initialized pointer without axis events");
    feed(input, EventKind::ButtonUp, 0, events);
    check(events.size() == 2
              && same(events[1], EventType::Release, {0, 0}, 1U, 0U),
          "initial button release is delivered immediately");

    events.clear();
    feed(input, EventKind::AbsoluteX, 799, events);
    check(events.empty(), "absolute axis updates remain pending until drain");
    drain(input, events);
    check(events.size() == 1
              && same(events[0], EventType::Motion, {799, 0}, 0U, 0U),
          "drain publishes X-only motion without waiting for Y");
    drain(input, events);
    check(events.size() == 1, "repeated drain omits unchanged coordinates");
    feed(input, EventKind::AbsoluteY, 1279, events);
    drain(input, events);
    check(events.size() == 2
              && same(events[1], EventType::Motion, {799, 1279}, 0U, 0U),
          "split Y update publishes independently on a later drain");
}

void testMotionBeforeButtons(const Layout &layout)
{
    Input input(layout, Rotation::R0, AxisRange{0, 799, 0, 1279});
    std::vector<Event> events;
    feed(input, EventKind::AbsoluteX, 799, events);
    feed(input, EventKind::ButtonDown, 0, events);
    check(events.size() == 2
              && same(events[0], EventType::Motion, {799, 0}, 0U, 0U)
              && same(events[1], EventType::Press, {799, 0}, 1U, 1U),
          "pending motion precedes a press transition");

    feed(input, EventKind::AbsoluteY, 1279, events);
    feed(input, EventKind::ButtonUp, 0, events);
    check(events.size() == 4
              && same(events[2], EventType::Motion, {799, 1279}, 0U, 1U)
              && same(events[3], EventType::Release, {799, 1279}, 1U, 0U),
          "pending motion precedes release and carries prior button state");
}

void testButtonBitsAndDuplicates(const Layout &layout)
{
    Input input(layout, Rotation::R0, AxisRange{0, 799, 0, 1279});
    std::vector<Event> events;
    feed(input, EventKind::ButtonDown, 0, events);
    feed(input, EventKind::ButtonDown, 0, events);
    feed(input, EventKind::ButtonDown, 1, events);
    feed(input, EventKind::ButtonDown, 2, events);
    feed(input, EventKind::ButtonUp, 1, events);
    feed(input, EventKind::ButtonUp, 1, events);
    feed(input, EventKind::ButtonUp, -1, events);
    feed(input, EventKind::ButtonDown, 3, events);
    feed(input, EventKind::ButtonUp, 0, events);
    feed(input, EventKind::ButtonUp, 2, events);

    check(events.size() == 6, "duplicate and unsupported button reports are ignored");
    if (events.size() == 6) {
        check(same(events[0], EventType::Press, {0, 0}, 1U, 1U),
              "wscons button index zero maps to left-button bit zero");
        check(same(events[1], EventType::Press, {0, 0}, 2U, 3U),
              "wscons button index one maps to middle-button bit one");
        check(same(events[2], EventType::Press, {0, 0}, 4U, 7U),
              "wscons button index two maps to right-button bit two");
        check(same(events[3], EventType::Release, {0, 0}, 2U, 5U),
              "middle-button release clears only its own bit");
        check(same(events[4], EventType::Release, {0, 0}, 1U, 4U),
              "left-button release preserves right-button state");
        check(same(events[5], EventType::Release, {0, 0}, 4U, 0U),
              "right-button release clears the final bit");
    }

    feed(input, static_cast<EventKind>(99), INT_MIN, events);
    drain(input, events);
    check(events.size() == 6, "unknown event kind produces no output");
}

void testClampAndWideRanges(const Layout &layout)
{
    Input clamped(layout, Rotation::R0, AxisRange{10, 20, 100, 200});
    std::vector<Event> events;
    feed(clamped, EventKind::AbsoluteX, INT_MIN, events);
    feed(clamped, EventKind::AbsoluteY, INT_MAX, events);
    drain(clamped, events);
    check(!events.empty()
              && same(events.back(), EventType::Motion, {0, 1279}, 0U, 0U),
          "out-of-range raw coordinates clamp to inclusive endpoints");
    feed(clamped, EventKind::AbsoluteX, INT_MAX, events);
    feed(clamped, EventKind::AbsoluteY, INT_MIN, events);
    drain(clamped, events);
    check(!events.empty()
              && same(events.back(), EventType::Motion, {799, 0}, 0U, 0U),
          "opposite out-of-range coordinates clamp to opposite endpoints");

    Input wide(layout, Rotation::R0, AxisRange{INT_MIN, INT_MAX, INT_MIN, INT_MAX});
    std::vector<Event> wideEvents;
    check(wide.valid(), "full signed integer calibration range is valid");
    feed(wide, EventKind::AbsoluteX, INT_MIN, wideEvents);
    feed(wide, EventKind::AbsoluteY, INT_MIN, wideEvents);
    drain(wide, wideEvents);
    check(!wideEvents.empty()
              && same(wideEvents.back(), EventType::Motion, {0, 0}, 0U, 0U),
          "wide calibration minimum maps without signed overflow");
    feed(wide, EventKind::AbsoluteX, INT_MAX, wideEvents);
    feed(wide, EventKind::AbsoluteY, INT_MAX, wideEvents);
    drain(wide, wideEvents);
    check(!wideEvents.empty()
              && same(wideEvents.back(), EventType::Motion, {799, 1279}, 0U, 0U),
          "wide calibration maximum maps without signed overflow");
}

void testInvalidInputs(const Layout &layout)
{
    struct InvalidCase {
        Layout layout{};
        AxisRange axes{0, 1, 0, 1};
    };
    std::array<InvalidCase, 5> cases{};
    cases[0] = {layout, {10, 10, 0, 100}};
    cases[1] = {layout, {20, 10, 0, 100}};
    cases[2] = {layout, {0, 100, 5, 5}};
    cases[3] = {layout, {0, 100, 20, 10}};
    cases[4] = {Layout{}, {0, 100, 0, 100}};

    for (const InvalidCase &test : cases) {
        Input input(test.layout, Rotation::R0, test.axes);
        std::vector<Event> events;
        check(!input.valid(), "invalid layout or calibration disables pointer input");
        feed(input, EventKind::AbsoluteX, INT_MAX, events);
        feed(input, EventKind::AbsoluteY, INT_MIN, events);
        feed(input, EventKind::ButtonDown, 0, events);
        drain(input, events);
        disconnect(input, events);
        check(events.empty(), "invalid pointer input emits no events");
    }
}

void testDisconnectReleasesButtons(const Layout &layout)
{
    Input input(layout, Rotation::R0, AxisRange{0, 799, 0, 1279});
    std::vector<Event> events;
    feed(input, EventKind::ButtonDown, 0, events);
    feed(input, EventKind::ButtonDown, 2, events);
    events.clear();

    feed(input, EventKind::AbsoluteX, 799, events);
    disconnect(input, events);
    check(events.size() == 3, "disconnect flushes motion and releases both pressed buttons");
    if (events.size() == 3) {
        check(same(events[0], EventType::Motion, {799, 0}, 0U, 5U),
              "disconnect publishes pending motion before releases");
        std::uint32_t released = 0;
        for (std::size_t i = 1; i < events.size(); ++i) {
            check(events[i].kind == EventType::Release,
                  "disconnect emits only button releases after pending motion");
            check(events[i].button == 1U || events[i].button == 4U,
                  "disconnect releases each pressed button exactly once");
            released |= events[i].button;
        }
        check(released == 5U && events.back().buttons == 0U,
              "disconnect leaves no pressed buttons");
    }

    disconnect(input, events);
    check(events.size() == 3, "repeated disconnect emits nothing");
}

} // namespace

int main()
{
    const Layout layout = testLayout();
    testRotationCorners(layout);
    testInitialPressAndAxisDrain(layout);
    testMotionBeforeButtons(layout);
    testButtonBitsAndDuplicates(layout);
    testClampAndWideRanges(layout);
    testInvalidInputs(layout);
    testDisconnectReleasesButtons(layout);
    if (failures != 0)
        std::cerr << failures << " pointer input checks failed\n";
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
