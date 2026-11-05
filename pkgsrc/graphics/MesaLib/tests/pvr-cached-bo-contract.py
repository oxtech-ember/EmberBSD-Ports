#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors.
"""Check the real CREATE_BO helper against old and cached-capable kernels."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def extract(text, name):
    match = re.search(r"static (?:VkResult|uint64_t)\s+" + name + r"\s*\(", text)
    if not match:
        raise ValueError("missing function " + name)
    opening = text.index("{", match.end())
    depth = 0
    for pos in range(opening, len(text)):
        depth += (text[pos] == "{") - (text[pos] == "}")
        if depth == 0:
            return text[match.start():pos + 1]
    raise ValueError("unterminated function " + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesa", type=Path, required=True)
    parser.add_argument("--cc", type=Path, required=True)
    parser.add_argument("--work-parent", type=Path, required=True)
    args = parser.parse_args()
    source = (args.mesa / "src/imagination/vulkan/winsys/powervr/pvr_drm_bo.c").read_text()
    harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef int VkResult;
#define VK_SUCCESS 0
#define VK_ERROR_OUT_OF_DEVICE_MEMORY (-2)
#define DRM_IOCTL_PVR_CREATE_BO 1
#define DRM_PVR_BO_BYPASS_DEVICE_CACHE (UINT64_C(1) << 0)
#define DRM_PVR_BO_PM_FW_PROTECT (UINT64_C(1) << 1)
#define DRM_PVR_BO_ALLOW_CPU_USERSPACE_ACCESS (UINT64_C(1) << 2)
#define DRM_PVR_BO_EMBER_CPU_CACHED (UINT64_C(1) << 63)
#define PVR_WINSYS_BO_FLAG_CPU_ACCESS (1U << 0)
#define PVR_WINSYS_BO_FLAG_GPU_UNCACHED (1U << 1)
#define PVR_WINSYS_BO_FLAG_PM_FW_PROTECT (1U << 2)
#define PVR_WINSYS_BO_FLAG_CPU_CACHED (1U << 3)
struct pvr_drm_winsys { struct { int render_fd; } base; };
struct drm_pvr_ioctl_create_bo_args { uint64_t size; uint32_t handle, pad; uint64_t flags; };
static uint64_t seen;
static bool supports_cached;
static VkResult pvr_ioctlf(int fd, int request,
    struct drm_pvr_ioctl_create_bo_args *args, VkResult error, const char *message)
{
   (void)fd; (void)request; (void)message;
   seen = args->flags;
   if (!supports_cached && (seen & DRM_PVR_BO_EMBER_CPU_CACHED))
      return error;
   args->handle = 37;
   return VK_SUCCESS;
}
''' + extract(source, "pvr_drm_create_gem_bo") + "\n" + extract(source, "pvr_drm_get_alloc_flags") + r'''
int main(void)
{
   struct pvr_drm_winsys ws = {0};
   uint32_t handle = 99;
   uint64_t flags = pvr_drm_get_alloc_flags(PVR_WINSYS_BO_FLAG_CPU_ACCESS |
                                           PVR_WINSYS_BO_FLAG_CPU_CACHED);
   assert(flags == UINT64_C(0x8000000000000004));
   assert(pvr_drm_create_gem_bo(&ws, flags, 4096, &handle) ==
          VK_ERROR_OUT_OF_DEVICE_MEMORY);
   assert(seen == flags && handle == 99);
   supports_cached = true;
   assert(pvr_drm_create_gem_bo(&ws, flags, 4096, &handle) == VK_SUCCESS);
   assert(seen == flags && handle == 37);
   supports_cached = false;
   flags = pvr_drm_get_alloc_flags(PVR_WINSYS_BO_FLAG_CPU_ACCESS);
   assert(pvr_drm_create_gem_bo(&ws, flags, 4096, &handle) == VK_SUCCESS);
   assert(seen == DRM_PVR_BO_ALLOW_CPU_USERSPACE_ACCESS);
   puts("PASS: cached BO flags and old-kernel rejection");
   return 0;
}
'''
    with tempfile.TemporaryDirectory(dir=args.work_parent, prefix="pvr-cached-") as work:
        cfile = Path(work) / "contract.c"
        binary = Path(work) / "contract"
        cfile.write_text(harness)
        subprocess.run([str(args.cc), "-std=c11", "-Wall", "-Wextra", "-Werror",
                        str(cfile), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
