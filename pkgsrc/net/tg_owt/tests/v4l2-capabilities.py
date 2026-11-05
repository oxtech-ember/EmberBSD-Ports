#!/usr/bin/env python3
"""Emit a target test of the actual helper from patched device_info_v4l2.cc."""
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()
match = re.search(r'uint32_t EffectiveCapabilities\(const struct v4l2_capability& cap\) \{[^}]*\}', source)
if not match:
    raise SystemExit('EffectiveCapabilities helper not found')
print('''#include <cstdint>
#include <sys/videoio.h>''')
print(match.group())
print('''
int main() {
  v4l2_capability c{};
  c.capabilities = V4L2_CAP_VIDEO_CAPTURE;
  c.device_caps = 0;
  if (!(EffectiveCapabilities(c) & V4L2_CAP_VIDEO_CAPTURE)) return 1;
  c.capabilities = V4L2_CAP_DEVICE_CAPS;
  c.device_caps = V4L2_CAP_VIDEO_CAPTURE;
  if (!(EffectiveCapabilities(c) & V4L2_CAP_VIDEO_CAPTURE)) return 2;
  c.capabilities = V4L2_CAP_DEVICE_CAPS | V4L2_CAP_VIDEO_CAPTURE;
  c.device_caps = 0;
  if (EffectiveCapabilities(c) & V4L2_CAP_VIDEO_CAPTURE) return 3;
  c.capabilities = 0;
  c.device_caps = V4L2_CAP_VIDEO_CAPTURE;
  if (EffectiveCapabilities(c) & V4L2_CAP_VIDEO_CAPTURE) return 4;
  return 0;
}''')
