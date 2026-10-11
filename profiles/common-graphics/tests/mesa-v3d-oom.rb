#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted actual-source V3D import allocation regression.
require 'fileutils'
require 'open3'
require 'digest'
abort 'usage: mesa-v3d-oom.rb MESA_SOURCE NEW_WORK' unless ARGV.length==2
source=File.realpath(ARGV[0]);work=File.expand_path(ARGV[1])
abort 'work already exists' if File.exist?(work)
FileUtils.mkdir_p(work)
path="#{source}/src/gallium/drivers/v3d/v3d_bufmgr.c"
text=File.read(path)
body=text[/^v3d_bo_open_handle\(.*?^}/m] or abort 'upstream function missing'
fixture=<<~'C'
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
struct pipe_reference { unsigned count; };
struct v3d_screen { void *bo_handles; int bo_handles_mutex, fd; unsigned bo_count, bo_size; };
struct v3d_bo { struct pipe_reference reference; struct v3d_screen *screen;
 uint32_t handle, size, offset; const char *name; bool private; void *map; };
struct drm_v3d_get_bo_offset { uint32_t handle, offset; };
#define DRM_IOCTL_V3D_GET_BO_OFFSET 7
#define USE_V3D_SIMULATOR 0
static bool fail_alloc, fail_ioctl;
static unsigned allocations, calls, insertions, unlocks;
static struct v3d_bo *cached;
static void *allocate(size_t size) { allocations++; return fail_alloc ? NULL : calloc(1,size); }
#define CALLOC_STRUCT(t) allocate(sizeof(struct t))
static void pipe_reference_init(struct pipe_reference *p,unsigned count) { p->count=count; }
static void pipe_reference(void *old,struct pipe_reference *p) { assert(!old);p->count++; }
static void *util_hash_table_get(void *table,void *key) { assert(table && (uintptr_t)key==9);return cached; }
static void _mesa_hash_table_insert(void *table,void *key,void *bo) {
 assert(table && (uintptr_t)key==9 && bo); insertions++;
}
static int v3d_ioctl(int fd,int op,struct drm_v3d_get_bo_offset *arg) {
 assert(fd==8 && op==7 && arg->handle==9);calls++;arg->offset=0x4000;
 return fail_ioctl ? -1 : 0;
}
#define mesa_loge(...) ((void)0)
static void mtx_unlock(int *lock) { assert(*lock==1);*lock=0;unlocks++; }
static struct v3d_bo *
C
main=<<~'C'
int main(void) {
 struct v3d_screen screen={.bo_handles=&screen,.fd=8,.bo_handles_mutex=1};
 fail_alloc=true;
 assert(v3d_bo_open_handle(&screen,9,4096)==NULL);
 assert(unlocks==1 && allocations==1 && calls==0 && insertions==0);
 assert(screen.bo_count==0 && screen.bo_size==0);
 fail_alloc=false;fail_ioctl=true;screen.bo_handles_mutex=1;
 assert(v3d_bo_open_handle(&screen,9,4096)==NULL);
 assert(unlocks==2 && calls==1 && insertions==0 && screen.bo_count==0);
 fail_ioctl=false;screen.bo_handles_mutex=1;
 struct v3d_bo *bo=v3d_bo_open_handle(&screen,9,4096);
 assert(bo && bo->offset==0x4000 && bo->reference.count==1 && !bo->private);
 assert(screen.bo_count==1 && screen.bo_size==4096 && insertions==1 && calls==2);
 cached=bo;screen.bo_handles_mutex=1;fail_alloc=true;
 assert(v3d_bo_open_handle(&screen,9,4096)==bo && bo->reference.count==2);
 assert(allocations==3 && calls==2 && insertions==1 && unlocks==4);
 free(bo);
 puts("PASS: actual V3D import body: allocation failure, ioctl failure, success and cached handle; lock released on every path");
}
C
File.write("#{work}/test.c",fixture+body+"\n"+main)
cmd=[ENV.fetch('CC','cc'),'-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',"#{work}/test.c",'-o',"#{work}/test"]
output,status=Open3.capture2e(*cmd);File.write("#{work}/build.log",output);abort output unless status.success?
output,status=Open3.capture2e("#{work}/test");File.write("#{work}/run.log",output)
File.write("#{work}/source.sha256","#{Digest::SHA256.file(path).hexdigest}  #{path}\n")
puts output
abort "actual-source regression failed: #{status}" unless status.success?
