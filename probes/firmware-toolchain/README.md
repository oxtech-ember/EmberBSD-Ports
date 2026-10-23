# Board-firmware toolchain probe

This probe holds the incomplete pkgsrc recipes for a GCC16 board-firmware
toolchain:

- `recipes/sysutils/dtc`: the device tree compiler.
- `recipes/cross/aarch64-none-elf-binutils`: Binutils 2.47 for bare-metal AArch64.
- `recipes/cross/aarch64-none-elf-gcc`: GCC16 for bare-metal AArch64.

The recipe Makefiles are missing. The GCC PLIST still describes the old
package. `scripts/prepare-pkgsrc.sh` does not export these recipes, and the
export uses the pinned upstream `sysutils/dtc` recipe. The pinned GCC8.2
firmware compiler is not a fallback.

To complete the probe, write the Makefiles, regenerate the PLIST files and
build the packages on the development host. Then move each complete recipe
to `pkgsrc/` and add each path that replaces an upstream recipe to
`pkgsrc/replaces`.
