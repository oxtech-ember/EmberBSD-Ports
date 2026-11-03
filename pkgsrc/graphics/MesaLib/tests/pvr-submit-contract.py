#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors.
"""Exercise actual Mesa submission and queue control flow with a fake kernel."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile


def function(text, name):
    matches = list(re.finditer(r"(?:static )?VkResult\s+" + name + r"\s*\(", text))
    match = matches[-1] if matches else None
    if not match:
        raise ValueError("missing function " + name)
    start = match.start()
    opening = text.index("{", match.end())
    depth = 0
    for pos in range(opening, len(text)):
        depth += (text[pos] == "{") - (text[pos] == "}")
        if depth == 0:
            return text[start:pos + 1]
    raise ValueError("unterminated function " + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesa", required=True, type=Path)
    parser.add_argument("--cc", required=True, type=Path)
    parser.add_argument("--work-parent", required=True, type=Path)
    args = parser.parse_args()
    root = args.mesa / "src/imagination/vulkan"
    winsys = root / "winsys/powervr"
    helper = (winsys / "pvr_drm_job_common.h").read_text()
    queue = function((root / "pvr_arch_queue.c").read_text(), "pvr_driver_queue_submit")
    upstream_macro = (root / "winsys/pvr_winsys_helper.h").read_text()
    macro = upstream_macro[upstream_macro.index("#define pvr_ioctlf"):upstream_macro.index("#define pvr_ioctl(")]
    if "pvr_drm_submit_jobs(" in helper:
        submit = function(helper, "pvr_drm_submit_jobs")
    else:
        compute = (winsys / "pvr_drm_job_compute.c").read_text()
        body = re.search(r'return pvr_ioctlf\(drm_ws->base.render_fd,\s*DRM_IOCTL_PVR_SUBMIT_JOBS,\s*&args,\s*VK_ERROR_OUT_OF_DEVICE_MEMORY,\s*"Failed to submit compute job"\);', compute)
        if body is None:
            raise ValueError("upstream submit expression changed")
        submit = "static VkResult pvr_drm_submit_jobs(int fd, struct drm_pvr_ioctl_submit_jobs_args *arg, const char *message) { struct pvr_drm_winsys local = { .base = { .render_fd = fd } }; struct pvr_drm_winsys *drm_ws = &local; struct drm_pvr_ioctl_submit_jobs_args args = *arg; (void)message; " + body.group(0) + " }"
    if "pvr_drm_submit_jobs(" in helper:
        for job in ("compute", "render", "transfer"):
            contents = (winsys / ("pvr_drm_job_" + job + ".c")).read_text()
            if not re.search(r"return\s+pvr_drm_submit_jobs\(", contents):
                raise ValueError("missing submit helper in " + job)
    for source in (submit, queue):
        if "#ifdef __NetBSD__" in source:
            raise ValueError("use #if defined(__NetBSD__) in source")
    submit = submit.replace("defined(__NetBSD__)", "TEST_NETBSD")
    queue = queue.replace("defined(__NetBSD__)", "TEST_NETBSD")
    harness = r'''
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef int VkResult;
#define VK_SUCCESS 0
#define VK_ERROR_OUT_OF_DEVICE_MEMORY -2
#define VK_ERROR_DEVICE_LOST -4
#define DRM_IOCTL_PVR_SUBMIT_JOBS 0x55
static int calls, executed, waits, job1, tail, lost, mode;
struct drm_pvr_ioctl_submit_jobs_args { int value; };
struct pvr_drm_winsys { struct { int render_fd; } base; };
static int raw_ioctl(int fd, unsigned long request, void *arg) {
  (void)fd; (void)request; (void)arg; calls++; executed++; waits++; if (mode == 2) { job1++; return 0; } errno = mode == 1 ? EAGAIN : mode == 4 ? EIO : EINTR; return -1;
}
static int drmIoctl(int fd, unsigned long request, void *arg) {
  int ret = raw_ioctl(fd, request, arg);
  if (ret && (errno == EINTR || errno == EAGAIN)) { calls++; executed++; waits++; job1++; return 0; }
  return ret;
}
#define ioctl raw_ioctl
static VkResult vk_errorf(void *object, VkResult error, const char *message, ...) {
  (void)object; (void)message; return error;
}
''' + macro + '\n' + submit + r'''
struct vk_queue { int dummy; };
struct pvr_device { int dummy; };
struct pvr_queue { struct vk_queue vk; struct pvr_device *device; };
struct pvr_cmd_buffer { int vk; };
struct vk_queue_submit { int wait_count; void *waits; unsigned command_buffer_count; int **command_buffers; void *signals; int signal_count; };
struct pvr_suspended_data { void *rts; };
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
static VkResult vk_queue_set_lost(struct vk_queue *queue, const char *message) { (void)queue; (void)message; lost++; return VK_ERROR_DEVICE_LOST; }
static VkResult pvr_clear_last_submits_syncs(struct pvr_queue *q) { (void)q; return mode == 5 ? VK_ERROR_DEVICE_LOST : VK_SUCCESS; }
static VkResult pvr_process_queue_waits(struct pvr_queue *q, void *w, int n) { (void)q; (void)w; (void)n; return VK_SUCCESS; }
static VkResult pvr_process_cmd_buffer(struct pvr_device *d, struct pvr_queue *q, struct pvr_cmd_buffer *c, struct pvr_suspended_data *s) { struct drm_pvr_ioctl_submit_jobs_args args = { 0 }; (void)d; (void)q; (void)c; (void)s; if (mode == 3) { executed++; return VK_ERROR_OUT_OF_DEVICE_MEMORY; } return pvr_drm_submit_jobs(1, &args, "compute"); }
static VkResult pvr_process_queue_signals(struct pvr_queue *q, void *signals, int n) { (void)q; (void)signals; (void)n; tail++; return VK_SUCCESS; }
''' + queue + r'''
int main(void) {
  struct pvr_device device = {0}; struct pvr_queue queue = { .device = &device };
  struct pvr_cmd_buffer command = {0}; int *cmd = &command.vk;
  struct vk_queue_submit submit = { .command_buffer_count = 1, .command_buffers = &cmd };
  VkResult result = pvr_driver_queue_submit(&queue.vk, &submit);
#if TEST_NETBSD
  if (result != VK_ERROR_DEVICE_LOST || calls != 1 || executed != 1 || waits != 1 || job1 != 0 || tail != 0 || lost != 1) {
    fprintf(stderr, "NetBSD replay/queue failure: result=%d calls=%d executed=%d tail=%d lost=%d\n", result, calls, executed, tail, lost); return 1;
  }
  calls = executed = waits = job1 = tail = lost = 0; mode = 1;
  result = pvr_driver_queue_submit(&queue.vk, &submit);
  if (result != VK_ERROR_DEVICE_LOST || calls != 1 || executed != 1 || waits != 1 || job1 != 0 || tail != 0 || lost != 1) return 2;
  calls = executed = waits = job1 = tail = lost = 0; mode = 3;
  result = pvr_driver_queue_submit(&queue.vk, &submit);
  if (result != VK_ERROR_DEVICE_LOST || executed != 1 || tail != 0 || lost != 1) return 3;
  calls = executed = waits = job1 = tail = lost = 0; mode = 4;
  result = pvr_driver_queue_submit(&queue.vk, &submit);
  if (result != VK_ERROR_DEVICE_LOST || calls != 1 || tail != 0 || lost != 1) return 5;
  calls = executed = waits = job1 = tail = lost = 0; mode = 5;
  result = pvr_driver_queue_submit(&queue.vk, &submit);
  if (result != VK_ERROR_DEVICE_LOST || calls != 0 || tail != 0 || lost != 1) return 8;
#else
  if (result != VK_SUCCESS || calls != 2 || executed != 2 || waits != 2 || job1 != 1 || tail != 1 || lost != 0) return 1;
  calls = executed = waits = job1 = tail = lost = 0; mode = 1;
  result = pvr_driver_queue_submit(&queue.vk, &submit);
  if (result != VK_SUCCESS || calls != 2 || executed != 2 || job1 != 1 || tail != 1 || lost != 0) return 7;
  calls = executed = waits = job1 = tail = lost = 0; mode = 4;
  result = pvr_driver_queue_submit(&queue.vk, &submit);
  if (result != VK_ERROR_OUT_OF_DEVICE_MEMORY || calls != 1 || tail != 0 || lost != 0) return 6;
#endif
  calls = executed = waits = job1 = tail = lost = 0; mode = 2;
  result = pvr_driver_queue_submit(&queue.vk, &submit);
  if (result != VK_SUCCESS || calls != 1 || executed != 1 || waits != 1 || job1 != 1 || tail != 1 || lost != 0) return 4;
  return 0;
}
'''
    with tempfile.TemporaryDirectory(dir=args.work_parent, prefix="pvr-submit-contract-") as work:
        source = Path(work) / "test.c"
        source.write_text(harness)
        for variant in (1, 0):
            output = Path(work) / ("netbsd" if variant else "linux")
            subprocess.run([str(args.cc), "-fuse-ld=" + str(args.cc.parent / "ld.lld"), "-std=gnu11", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-DTEST_NETBSD=" + str(variant), str(source), "-o", str(output)], check=True)
            subprocess.run([str(output)], check=True)
    print("PASS: real Mesa submit/queue paths: one-shot NetBSD, unchanged Linux")


if __name__ == "__main__":
    main()
