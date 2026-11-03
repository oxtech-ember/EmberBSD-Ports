# Shared PowerVR firmware package

`sysutils/powervr-firmware` owns the unmodified runtime firmware inputs.
Mesa owns its Vulkan ICD separately. Firmware files are not host SDK tools.

The recipe pins Imagination's firmware repository at
`8a58f81883f7be458daa34e418cc4079f995b279` and retains its `LICENSE.powervr`
and `WHENCE`. The license permits unmodified binary redistribution under
its stated conditions. The package does not modify or disassemble firmware.

| BVNC | Installed file under `libdata/firmware/powervr` |
| --- | --- |
| `22.102.54.38` | `rogue_22.102.54.38_v1.fw` |
| `36.56.104.183` | `rogue_36.56.104.183_v1.fw` |

Both files identify firmware interface `1.1.OS@6976702`. The native driver
must still validate its exact BVNC, metadata, features and image layout.
The GE8300 file is a preparation input; hardware rendering remains unaccepted.

The standard EmberBSD firmware search path includes
`/usr/pkg/libdata/firmware`. The package also installs the license alongside
the images and keeps `WHENCE` in `share/doc/powervr-firmware`.
It does not alter firmware search sysctls or select a kernel GPU profile.

For a selected licensed Imagination target, enable the package's license
in that build configuration:

```make
ACCEPTABLE_LICENSES+= powervr-firmware-license
```

This setting remains scoped to the selected configuration.
Use the normal package target from a current shared export. The package
copies data and runs no compiler or target executable. Package validation
and installed driver acceptance are separate checks.
