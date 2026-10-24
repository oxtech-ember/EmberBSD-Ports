// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
#include <linux/input.h>

#include <cstdint>
#include <limits>
#include "ui/events/keycodes/dom/keycode_converter.h"

static_assert(KEY_RESERVED == 0 && KEY_MAX == 0x2ff);
static_assert(KEY_A == 30 && KEY_ENTER == 28 && KEY_LEFTCTRL == 29);
static_assert(KEY_PAUSE == 119 && KEY_PLAYPAUSE == 164);
static_assert(KEY_PLAYCD == 200 && KEY_PLAY == 207);

int main() {
  using ui::DomCode;
  using ui::KeycodeConverter;
  struct Expected { int evdev; uint32_t xkb; DomCode dom; };
  constexpr Expected cases[] = {
      {30, 38, DomCode::US_A}, {28, 36, DomCode::ENTER},
      {29, 37, DomCode::CONTROL_LEFT}, {119, 127, DomCode::PAUSE},
      {164, 172, DomCode::MEDIA_PLAY_PAUSE}, {207, 215, DomCode::MEDIA_PLAY},
  };
  int failure = 1;
  for (const auto& expected : cases) {
    if (KeycodeConverter::EvdevCodeToDomCode(expected.evdev) != expected.dom)
      return failure;
    ++failure;
    if (KeycodeConverter::DomCodeToEvdevCode(expected.dom) != expected.evdev)
      return failure;
    ++failure;
    if (KeycodeConverter::XkbKeycodeToDomCode(expected.xkb) != expected.dom)
      return failure;
    ++failure;
    if (KeycodeConverter::DomCodeToXkbKeycode(expected.dom) != expected.xkb)
      return failure;
    ++failure;
  }
  if (KeycodeConverter::DomCodeToNativeKeycode(DomCode::US_A) != 38) return 25;
  if (KeycodeConverter::NativeKeycodeToDomCode(38) != DomCode::US_A) return 26;
  constexpr int invalid[] = {std::numeric_limits<int>::min(), -1, 0, 0x2ff,
                             0x300, std::numeric_limits<int>::max()};
  failure = 32;
  for (int code : invalid) {
    if (KeycodeConverter::EvdevCodeToDomCode(code) != DomCode::NONE)
      return failure;
    ++failure;
  }
  if (KeycodeConverter::XkbKeycodeToDomCode(7u) != DomCode::NONE) return 40;
  if (KeycodeConverter::XkbKeycodeToDomCode(8u) != DomCode::NONE) return 41;
  if (KeycodeConverter::XkbKeycodeToDomCode(std::numeric_limits<uint32_t>::max())
      != DomCode::NONE) return 42;
  if (KeycodeConverter::DomCodeToEvdevCode(DomCode::NONE) != 0) return 43;
  if (KeycodeConverter::DomCodeToEvdevCode(static_cast<DomCode>(0xffffff)) != 0)
    return 44;
  if (KeycodeConverter::EvdevCodeToDomCode(200) != DomCode::MEDIA_PLAY) return 48;
  if (KeycodeConverter::EvdevCodeToDomCode(207) != DomCode::MEDIA_PLAY) return 49;
  if (KeycodeConverter::DomCodeToEvdevCode(DomCode::MEDIA_PLAY) != 207) return 50;
  return 0;
}
