# GCC16 firmware C frontend

`build-firmware.py` requires `--target arm-none-eabi`. This separate target
policy does not add an application or kernel architecture. It prepares
GCC 16.2.0's C frontend and the pinned Binutils 2.47 in a new private prefix.
It reuses source, patch, host math and process helpers from
[the cross profile](README.md). The host must provide GCC16 and G++16. It builds `all-gcc` and installs `install-gcc`.
It does not build newlib, libgcc, C++ libraries or an application sysroot.

Use the same prepared `lang/gcc16` source recipe, original GCC archive,
host GNU make and optional host math prefix as the kernel frontend build:

```sh
HOST_CC=gcc-16 HOST_CXX=g++-16 CROSS_JOBS=2 \
    python3 -B profiles/development-toolchain/cross/build-firmware.py \
    --target arm-none-eabi /absolute/pkgsrc /absolute/gcc-16.2.0.tar.xz \
    /absolute/os-tools /absolute/host-math/prefix /absolute/new-firmware-gcc16 \
    --sdk-source /absolute/EmberBSD-SDK
```

The default CPU is Cortex-M4 in Thumb mode with the soft floating-point ABI.
The builder checks the installed compiler version, triplet, macros and GNU
tool paths. It also assembles one Thumb function and checks its relocatable
ELF32 ARM EABI5 object. Use explicit flags for a firmware source:

```sh
/absolute/new-firmware-gcc16/toolchain/bin/arm-none-eabi-gcc \
    -mthumb -mcpu=cortex-m4 -mfloat-abi=soft \
    -c -x assembler-with-cpp extension.S -o extension.o
```

The host regression checks target refusals, input identities, frontend-only
commands and ELF rejection paths without building a compiler:

```sh
python3 -I -B profiles/development-toolchain/cross/tests/firmware-host.py \
    --sdk-source /absolute/EmberBSD-SDK
```

These host fixtures do not qualify an ARM compiler build. An actual toolchain
build, firmware layout, key ownership and device execution need separate
acceptance. This profile does not establish ARM OS or userland support.
