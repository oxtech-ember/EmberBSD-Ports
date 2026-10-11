/* Origin: EmberBSD; AI-assisted libdrm native API boundary fixtures. */
/* SPDX-License-Identifier: BSD-2-Clause */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <sys/stat.h>
#include <unistd.h>
#include "xf86drm.h"
#include "drm_native_identity.h"
#undef __linux__
#define __NetBSD__ 1
#define DRM_MAJOR 180
#define DRM_BUS_VIRTIO 0x10
#define MAX_DRM_NODES 256
#define ALIGN(x,y) (((x)+(y)-1)&~((y)-1))
#define MAX2(x,y) ((x)>(y)?(x):(y))
#define MAX3(x,y,z) MAX2(MAX2(x,y),z)
#define MIN2(x,y) ((x)<(y)?(x):(y))
static struct drm_native_pci_record records[2];
static struct drm_native_platform_record platform;
static size_t platform_length=160;
static bool platform_enabled;
static int no_metadata, metadata_error, legacy_calls;
static bool missing_render, reused_render;
static size_t returned_length=68;
static int sysctlbyname(const char *name, void *buf, size_t *len,
    const void *newp, size_t newlen)
{
    int min;
assert(!newp && !newlen);
if (sscanf(name,"hw.drm2.platform%d",&min)==1) {
    assert(*len==160);
    if (metadata_error) { errno=metadata_error; return -1; }
    if (platform_enabled && (min==3 || min==140)) {
        memcpy(buf,&platform,160); *len=platform_length; return 0;
    }
    errno=ENOENT; return -1;
}
assert(*len==68);
    assert(sscanf(name,"hw.drm2.identity%d",&min)==1);
    if (metadata_error) { errno=metadata_error; return -1; }
    if (!no_metadata) for (int i=0; i<2; i++) {
        if (platform_enabled && i==0) continue;
        if (records[i].primary_minor==(uint32_t)min || records[i].render_minor==(uint32_t)min) {
            memcpy(buf,&records[i],68); *len=returned_length; return 0;
        }
    }
    errno=ENOENT; return -1;
}
static int fake_stat(const char *path, struct stat *sb)
{
    memset(sb,0,sizeof(*sb));
    for (int i=0; i<2; i++) for (int type=0; type<2; type++) {
        char want[64]; unsigned min=type ? records[i].render_minor : records[i].primary_minor;
        snprintf(want,sizeof(want),type ? "/dev/dri/renderD%u" : "/dev/dri/card%u",min);
        if (strcmp(path,want)) continue;
        if (missing_render && type && i==0) { errno=ENOENT; return -1; }
        sb->st_mode=S_IFCHR|0660;
        sb->st_rdev=makedev(reused_render && type && i==0 ? 99U : 180U,min);
        return 0;
    }
    errno=ENOENT; return -1;
}
#define stat(p,s) fake_stat(p,s)
static int fake_fstat(int fd, struct stat *sb) {
    if (fd<0) { errno=EBADF; return -1; }
    memset(sb,0,sizeof(*sb)); sb->st_mode=S_IFCHR; sb->st_rdev=makedev(180U,fd); return 0;
}
#define fstat fake_fstat
static int fake_access(const char *p, int mode) { struct stat s; (void)mode; return fake_stat(p,&s); }
#define access fake_access
static int drmOpenMinor(int min, int create, int type) {
    (void)min; (void)create; (void)type; legacy_calls++; errno=EACCES; return -1;
}
int drmSetInterfaceVersion(int fd, drmSetVersion *v) { (void)fd; (void)v; legacy_calls++; return -EACCES; }
char *drmGetBusid(int fd) { (void)fd; legacy_calls++; return NULL; }
static int drmParsePciBusInfo(int maj, int min, drmPciBusInfo *info) {
    (void)maj; (void)min; (void)info; legacy_calls++; return -EACCES;
}
static int drmParsePciDeviceInfo(int maj, int min, drmPciDeviceInfo *info, uint32_t flags) {
    (void)maj; (void)min; (void)info; (void)flags; legacy_calls++; return -EACCES;
}
#define drmProcessUsbDevice(...) (-EINVAL)
#define drmProcessHost1xDevice(...) (-EINVAL)
#define drmProcessFauxDevice(...) (-EINVAL)
struct dirent { char d_name[64]; };
typedef struct { int pos; } DIR;
static DIR directory;
static DIR *opendir(const char *path) { assert(!strcmp(path,"/dev/dri")); directory.pos=0; return &directory; }
static struct dirent *readdir(DIR *d) {
    static struct dirent ent;
    if (d->pos==4) return NULL;
    int pos=d->pos++, i=pos/2;
    snprintf(ent.d_name,sizeof(ent.d_name),pos%2 ? "renderD%u" : "card%u",
        pos%2 ? records[i].render_minor : records[i].primary_minor);
    return &ent;
}
static int closedir(DIR *d) { assert(d==&directory); return 0; }
