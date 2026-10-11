/* Origin: EmberBSD; AI-assisted production libdrm discovery assertions. */
/* SPDX-License-Identifier: BSD-2-Clause */
int main(void)
{
    drmDevicePtr devices[4]={0}, device=NULL;
    struct drm_native_pci_record record;
    char *name;
    assert(sizeof(record)==68);
    records[0]=(struct drm_native_pci_record){
        .version=1,.length=68,.flags=7,.bus_type=1,.domain=2,.bus=4,
        .device=3,.function=1,.vendor=0x1af4,.product=0x1050,
        .subvendor=0xabcd,.subproduct=0x1234,.revision=9,
        .primary_major=180,.primary_minor=3,.render_major=180,.render_minor=140
    };
    records[1]=records[0]; records[1].primary_minor=7; records[1].render_minor=129;
    records[1].bus=5; records[1].product=0x1051;
    /* No primary master or global device access exists in this fixture. */
    assert(drmGetDevices2(0,devices,4)==2);
    for(int i=0;i<2;i++) {
        assert(devices[i]->available_nodes==5);
        assert(devices[i]->deviceinfo.pci->vendor_id==0x1af4);
        assert(devices[i]->deviceinfo.pci->subvendor_id==0xabcd);
        assert(devices[i]->deviceinfo.pci->revision_id==0xff);
    }
    assert(!strcmp(devices[0]->nodes[2],"/dev/dri/renderD140"));
    assert(!strcmp(devices[1]->nodes[2],"/dev/dri/renderD129"));
    drmFreeDevices(devices,2);
    assert(drmGetDevice2(140,DRM_DEVICE_GET_PCI_REVISION,&device)==0);
    assert(device->businfo.pci->bus==4 && device->deviceinfo.pci->revision_id==9);
    drmFreeDevice(&device);
    assert(drmGetNodeTypeFromFd(140)==DRM_NODE_RENDER);
    assert(drmGetNodeTypeFromFd(3)==DRM_NODE_PRIMARY);
    name=drmGetRenderDeviceNameFromFd(3); assert(name && !strcmp(name,"/dev/dri/renderD140")); free(name);
    name=drmGetRenderDeviceNameFromFd(140); assert(name && !strcmp(name,"/dev/dri/renderD140")); free(name);
    assert(legacy_calls==0);
    assert(drmGetDevice2(140,2,&device)==-EINVAL && !device);
    assert(drmGetDevices2(2,devices,4)==-EINVAL);
    assert(drmGetDevice2(-1,0,&device)==-EINVAL);
    missing_render=true;
    assert(!drmGetRenderDeviceNameFromFd(3));
    assert(drmGetDevice2(140,0,&device)==-ENODEV);
    missing_render=false; reused_render=true;
    assert(!drmGetRenderDeviceNameFromFd(3));
    assert(drmGetDevice2(140,0,&device)==-ENODEV);
    reused_render=false;
    records[0].version=2;
    assert(drmNativeIdentity(180,140,&record)==-EPROTO);
    assert(drmGetDevice2(140,0,&device)<0);
    records[0].version=1; records[0].flags|=8;
    assert(drmNativeIdentity(180,140,&record)==-EPROTO);
    records[0].flags=7; returned_length=64;
    assert(drmNativeIdentity(180,140,&record)==-EPROTO); returned_length=68;
    records[0].flags=3;
    assert(drmGetDevice2(140,1,&device)==-ENODEV);
    assert(drmGetDevice2(140,0,&device)==0); drmFreeDevice(&device);
    records[0].flags=7;
    metadata_error=EACCES;
    assert(drmNativeIdentity(180,140,&record)==-EACCES); metadata_error=0;
    assert(legacy_calls==0);
platform_enabled=true;
platform=(struct drm_native_platform_record) {
    .version=1,.length=160,.flags=3,.bus_type=DRM_NATIVE_BUS_PLATFORM,
    .primary_major=180,.primary_minor=3,.render_major=180,.render_minor=140,
    .fullname="bcmv3d0",.compatible="acpi:BCM2850"
};
assert(drmGetDevices2(0,devices,4)==2);
assert(devices[0]->bustype==DRM_BUS_PLATFORM);
assert(devices[0]->available_nodes==5);
assert(!strcmp(devices[0]->businfo.platform->fullname,"bcmv3d0"));
assert(!strcmp(devices[0]->deviceinfo.platform->compatible[0],"acpi:BCM2850"));
assert(devices[0]->deviceinfo.platform->compatible[1]==NULL);
assert(devices[1]->bustype==DRM_BUS_PCI);
drmFreeDevices(devices,2);
assert(drmGetDevice2(140,0,&device)==0 && device->bustype==DRM_BUS_PLATFORM);
drmFreeDevice(&device);
assert(drmGetNodeTypeFromFd(140)==DRM_NODE_RENDER);
assert(drmGetNodeTypeFromFd(3)==DRM_NODE_PRIMARY);
name=drmGetRenderDeviceNameFromFd(3);
assert(name && !strcmp(name,"/dev/dri/renderD140")); free(name);
missing_render=true;
assert(!drmGetRenderDeviceNameFromFd(3)); missing_render=false;
reused_render=true;
assert(!drmGetRenderDeviceNameFromFd(3)); reused_render=false;
struct drm_native_platform_record saved=platform, result;
for (int field=0;field<9;field++) {
    platform=saved;
    switch(field) {
    case 0: platform.version++;break;
    case 1: platform.length--;break;
    case 2: platform.flags|=4;break;
    case 3: platform.bus_type=DRM_NATIVE_BUS_PCI;break;
    case 4: platform.primary_minor=64;break;
    case 5: platform.render_minor=192;break;
    case 6: memset(platform.fullname,'x',sizeof(platform.fullname));break;
    case 7: platform.compatible[0]=0;break;
    case 8: platform_length=159;break;
    }
    /* Query the primary if the malformed field changed render membership. */
    assert(drmNativePlatformIdentity(180,3,&result)==-EPROTO ||
        (field==4 && drmNativePlatformIdentity(180,140,&result)==-EPROTO));
    assert(drmGetDevice2(140,0,&device)<0 && !device);
    platform_length=160;
}
platform=saved;
metadata_error=EACCES;
assert(drmNativePlatformIdentity(180,140,&result)==-EACCES);
metadata_error=0;
assert(legacy_calls==0);
platform_enabled=false;
    no_metadata=1;
    assert(drmGetDevice2(140,0,&device)<0 && legacy_calls>0);
    puts("PASS: production libdrm APIs, independent indices, folding, flags, missing/reused nodes, schema rejection and legacy fallback");
    return 0;
}
