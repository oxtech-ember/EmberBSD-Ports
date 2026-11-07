# Common U-Boot sources

`u-boot-source` installs the patched U-Boot release under
`share/u-boot-source`. It prepares source only; it does not build or install
firmware, select a board, or change the version used by existing U-Boot
packages.

The package applies the owner patch set and board files, then populates the
U-Boot libfdt and zlib integration from the shared `dtc-libfdt-source` and
`zlib-source` packages. U-Boot's `libfdt_env.h` remains its integration adapter.
A firmware consumer should include `Makefile.common`, declare the matching
source package as a build tool dependency, copy the installed source into its
own work directory and select host and target tools separately.

The source package does not establish board, image-format or runtime support.
The embedded upstream Mbed TLS source is excluded. A consumer enabling its
backend must populate `lib/mbedtls/external/mbedtls` with a compatible source
prepared by the common Ports owner, including its complete patch set, before
building. Selecting that backend without the source stops the build explicitly.
This receiver does not establish Mbed TLS backend compatibility or support.

## ESP32-S31 RAM firmware FIT

The S31 board files include a `firmware.its` template for OpenSBI, U-Boot
proper and the firmware FDT. This profile requires at least 16 MiB PSRAM.
Supply compatible artifacts and verify their load and runtime memory ranges
before use: the template loads OpenSBI at `0x2f000000`, U-Boot at
`0x50400000` and the firmware FDT at `0x50430000`. The FDT must have actual
space in its header for SPL and OpenSBI fixups. A 12 KiB padded input was
used in the initial trial; check the result for the selected FDT and fixups.

With a writable `WORK` directory and explicit `SOURCE`, `HOST_PREFIX`,
`MKIMAGE`, `OPENSBI_BIN`, `UBOOT_BIN` and `FIRMWARE_DTB` inputs:

```sh
cp "$SOURCE/board/espressif/esp32s31/firmware.its" "$WORK/firmware.its"
cp "$OPENSBI_BIN" "$WORK/opensbi.bin"
cp "$UBOOT_BIN" "$WORK/u-boot.bin"
"$HOST_PREFIX/bin/dtc" -I dtb -O dtb -S 12288 \
    -o "$WORK/firmware.dtb" "$FIRMWARE_DTB"
(cd "$WORK" && PATH="$HOST_PREFIX/bin:$HOST_PREFIX/gnu/bin" && export PATH &&
    "$MKIMAGE" -E -f firmware.its firmware.itb)
```

The `-E` form places data externally in firmware, U-Boot, FDT order for the
sequential SPL YMODEM reader. Each image has a SHA-256 integrity hash; it is
not authenticated. YMODEM defers FIT-owned progress until the transfer ends;
this does not suppress output from an FPGA backend. The S31 SPL does not enable
FPGA support. Run `tests/test-s31-fit-selector.py` from the Ports recipe
with `--source`, `--host-prefix` and `--fit "$WORK/firmware.itb"` to exercise
the actual SPL configuration selector and require the three ordered images to
use bounded external data. An inline FIT makes SPL size its allocation for the
entire payload instead of the small FIT structure and is rejected. Check the
generated data offsets, hashes, FDT capacity and memory map for the chosen
inputs separately.

For a RAM-loaded firmware FIT that needs the kernel to access mapped NOR, set
`CONFIG_ESP32S31_NOR_MAP=y`, `CONFIG_ESP32S31_NOR_BOOT` unset and
`CONFIG_ESP32S31_NOR_PROBE` unset. SPL attaches the ROM NOR interface during
initialization, then keeps UART/YMODEM as its only image source. For persistent
NOR-first boot, enable `CONFIG_ESP32S31_NOR_BOOT`; SPL tries NOR before its UART
fallback. Keep these modes explicit when selecting or producing an SPL image.

### S31 NOR image from prepared inputs

`board/espressif/esp32s31/make-nor-image.py` assembles a 16 MiB NOR image
from an already prepared ESP32-S31 ROM-format SPL, OpenSBI, U-Boot proper
binary and matching ELF, firmware DTB, nested kernel FIT and matching ELF,
and a root filesystem. RAM mode remains the default: it includes exactly
4 MiB of root data as a FIT loadable for PSRAM. NOR mode instead places the
root data directly in a caller-selected erase-aligned NOR partition; the
root is omitted from the FIT loadables. It checks ROM geometry, segment
ranges and digest, U-Boot ELF load and BSS bounds, FIT/partition non-overlap,
flash capacity, payload layout and SHA-256 integrity. External FIT payloads
are 512-byte aligned. The output must not already exist.

```sh
"$HOST_PREFIX/bin/python3.15" "$SOURCE/board/espressif/esp32s31/make-nor-image.py" \
    --host-prefix "$HOST_PREFIX" --mkimage "$MKIMAGE" \
    --spl-rom "$SPL_ROM" --opensbi "$OPENSBI_BIN" \
    --uboot "$UBOOT_BIN" --uboot-elf "$UBOOT_ELF" \
    --firmware-dtb "$FIRMWARE_DTB" --kernel-fit "$KERNEL_FIT" \
    --kernel-elf "$KERNEL_ELF" \
    --root-fs "$ROOT_FS" --output "$NOR_IMAGE"
```

For an external flash root, select the mode and provide the partition geometry
and the exact bootargs to store in the firmware FDT's `/chosen` node. For
example, a 6 MiB read-only boot prefix and 10 MiB root partition use:

```sh
    --root-mode nor --root-offset 0x600000 --root-size 0xa00000 \
    --erase-size 4096 \
    --bootargs 'root=flash1 mtdparts=espnor0:6M@0(boot)ro,10M@6M(root)'
```

The producer sets `/chosen/emberbsd,root-mode` to `nor` and copies these
bootargs into `/chosen/bootargs`. U-Boot selects a kernel-only `bootm` when
that explicit mode marker is present; otherwise the existing RAM-root
loadable validation and boot command remain active. Device names, partition
offsets and erase geometry come from the producer's profile inputs, not the
generic board hook. The flash-root layout is a preparation contract and does
not establish a writable filesystem or hardware acceptance.

Use `mkimage` from the common `sysutils/u-boot-tools` package in the host
prefix; `dtc`, `fdtget`, `llvm-objcopy`, and `llvm-readobj` also come from
that prefix. Prepare the ROM-format SPL with the selected target BFD `nm` and
`objcopy`, prefix Python and the official esptool. Preserve the appended DTB:

```sh
"$HOST_PREFIX/bin/python3.15" -c 'import pathlib,sys; a,b=(pathlib.Path(x).read_bytes() for x in sys.argv[1:]); sys.exit(0 if a.endswith(b) and b else 1)' "$SPL_BIN" "$SPL_DTB"
SPL_END=$("$TARGET_NM" -n "$SPL_ELF" | "$HOST_PREFIX/bin/nawk" '$3 == "_end" { print "0x" $1; found=1 } END { if (!found) exit 1 }')
"$TARGET_OBJCOPY" --add-section ".spl_dtb=$SPL_DTB" \
    --set-section-flags .spl_dtb=alloc,load,readonly,data,contents \
    --change-section-address ".spl_dtb=$SPL_END" "$SPL_ELF" "$IMAGE_ELF"
"$ESPTOOL" --chip esp32s31 elf2image --flash-mode dio --flash-freq 40m \
    --flash-size 16MB --output "$SPL_ROM" "$IMAGE_ELF"
```

Set `SPL_BIN`, `SPL_DTB` and `SPL_ELF` to the matching build artifacts;
`IMAGE_ELF` and `SPL_ROM` are separate output paths. The ROM image is an input
to the producer above. This produces
an image only; it does not write a device, establish a bootable NOR loader,
authenticate FIT data, or validate target execution. OpenSBI and SPL runtime
BSS, heap, stack and handoff need separate validation.

For a new root or kernel payload with an unchanged producer, FIT format and
boot chain, invoke the producer once. Its input, range, layout and payload
hash checks validate that image. The host checks cover separate code contracts:

- `tests/test-s31-nor.py` checks producer input validation. Run it when that
  implementation or contract changes.
- `tests/test-s31-nor-bootcmd.py` checks U-Boot's boot command and loadable
  contract. Run it when that boot-selection contract changes.
- `tests/test-s31-nor-integration.py` deliberately builds two complete images
  to check deterministic output and NOR offsets. Run it when the producer,
  FIT format or boot chain changes, or for explicit image qualification; it is
  not needed for each payload-only update.

### Opt-in Mosaico LCD command

The S31 proper board has an off-by-default `ESP32S31_MOSAICO_SPLASH` option.
The source package installs a one-symbol fragment at
`configs/espressif_esp32s31_mosaico_splash.fragment`. Apply it to a normal S31
configuration with U-Boot's `merge_config.sh` interface, then resolve the
configuration before building:

```sh
make -C "$SOURCE" O="$OBJDIR" espressif_esp32s31_defconfig
"$SOURCE/scripts/kconfig/merge_config.sh" -m -O "$OBJDIR" \
    "$OBJDIR/.config" \
    "$SOURCE/configs/espressif_esp32s31_mosaico_splash.fragment"
make -C "$SOURCE" O="$OBJDIR" olddefconfig
```

The option adds the manual `mosaicosplash red` U-Boot proper command; it is
not called by normal boot. It drives the V1.2 panel power/reset and SPI2 pins,
replays the Claw initialization sequence, and sends a solid red RGB565 frame.
This bounded diagnostic adaptation follows Espressif's Apache-2.0
`mosaico_boot_splash.c` at
[`2654a4a9f76f5d7ea108e4dff7ade7b1df4c1c5c`](https://github.com/espressif/esp-mosaico-claw/blob/2654a4a9f76f5d7ea108e4dff7ade7b1df4c1c5c/components/mosaico_boot_splash/bootloader/mosaico_boot_splash.c);
it is not byte-identical to the Claw implementation. Its MMIO transaction
sequence is covered by `tests/test-s31-mosaico-splash.py`; that host fixture
does not establish panel response or visible output.

## ESP32-S31 NOR profiles

`espressif_esp32s31_nor_probe_defconfig` maps the 16 MiB unencrypted NOR
and prints CRC-32 values for 4 KiB regions at offsets `0x2000` and `0x20000`
while retaining UART FIT boot. It invokes the ROM flash attach routine for
strapped pins and the documented slow-read setup; it does not issue flash
write commands. Run the probe from RAM and compare against an independently
saved flash image before using the persistent profile. The hardware cache and
controller state depends on the ROM boot path and must be verified on device.

`espressif_esp32s31_nor_defconfig` tries the FIT at NOR offset `0x20000`,
then UART on ordinary loading failure. A bus stall may prevent fallback. The
bounded NOR callback covers the normal SPL loader;
the upstream Falcon direct-access path is outside that contract and is not
enabled in this S31 profile. The profile uses ESP ROM image offset `0x2000`
and a 16 MiB NOR range. A producer must validate the complete ROM image,
FIT bounds and hashes, the memory map, a 4 MiB root image, and the selected
kernel FIT. Autostart is enabled only when the verified firmware FDT records
root and kernel at the profile addresses. The console can interrupt boot.
Neither configuration supports encrypted flash; hashes provide integrity,
not authentication. Preparing source or an image does not itself establish
successful persistent boot.

When building a configured U-Boot output tree with the selected native
prefix, append `PYTHON3="$HOST_PREFIX/bin/python3.15"` and
`DTC="$HOST_PREFIX/bin/dtc"` to the normal `gmake` invocation. Pass them as
make command-line variables: U-Boot's Makefile assignments override
environment variables and otherwise select ambient `python3` and `dtc`.

## Host regression checks

The scripts in `tests/` use an explicitly prepared U-Boot source tree and a
native Ports prefix containing Clang/LLD, Python, libfdt and, for the FIT hash
check, OpenSSL. Run them with the prefix Python. For example, with `SOURCE`
and `HOST_PREFIX` set to those directories:

```sh
for check in test-sha256.py test-spl-strings.py test-fit-flow.py \
    test-fit-read.py test-fit-hash.py test-psram-layout.py test-reserve.py test-s31-mpll.py \
    test-mips-endian.py test-prof-align.py test-env-awk.py \
    test-spl-nor-bounds.py test-s31-nor-map.py test-s31-nor-order.py \
    test-s31-mosaico-splash.py \
    test-s31-nor-bootcmd.py test-s31-nor-attach.py; do
    "$HOST_PREFIX/bin/python3.15" "tests/$check" \
        --source "$SOURCE" --host-prefix "$HOST_PREFIX" || exit 1
done
```

The S31 MPLL test uses a simulated MMIO bus to check both analog controller
selections, register ordering and timeout propagation; it does not establish
real analog clock or hardware behavior.

`test-env-awk.py` also needs native `nawk`. The FIT tests construct small
synthetic host fixtures; they do not create a board firmware image. The FIT
hash fixture uses OpenSSL for its digest collaborator. The FIT flow, PSRAM and
reservation fixtures extract the named production functions but mock their
surrounding environment. The reservation fixture models the recorded RV32
sizes and address map, not the sizes of an arbitrary future build.

Two checks take explicit inputs rather than embedding target artifacts:

```sh
"$HOST_PREFIX/bin/python3.15" tests/test-gzip.py --source "$SOURCE" \
    --host-prefix "$HOST_PREFIX" --raw "$RAW" --gzip "$GZIP" --zlib "$ZLIB"
"$HOST_PREFIX/bin/python3.15" tests/test-lmb.py --source "$SOURCE" \
    --host-prefix "$HOST_PREFIX" --kernel-flat "$RAW" --os-dtb "$OS_DTB" \
    --firmware-dtb "$FIRMWARE_DTB"
```

The three compression inputs must contain the same payload; the gzip harness
allows at most 6 MiB of uncompressed data. The LMB fixture uses the flat file
length, mocks memory mapping and parts of reserved-memory handling, and does
not establish the kernel's BSS span or actual hardware placement. These
checks do not produce a combined firmware FIT.

For an existing configured build, `tests/analyze-fit.py --source "$SOURCE"
--host-prefix "$HOST_PREFIX" --build-dir "$BUILD_DIR"` runs Clang static
analysis on the two FIT modules using their recorded target compile flags.
It reports findings; it does not classify inherited findings as clean.

The 2026.10 receiver was built with native and RV32 Clang, and the S31 SPL and
U-Boot proper linked from its prepared source. The listed host checks ran with
ASan and UBSan; gzip also ran against the existing 4,351,944-byte flat kernel.
Clang analysis of FIT and S31 paths reported existing header dead stores and
existing FIT findings; Cppcheck reported existing MMIO-header findings in its
selected configuration. These are not blanket clean results. The host endian
check exercised field conversions on the available little-endian host; it did
not test a big-endian host runtime.

These checks do not execute target MMIO, cache, clocks, UART, PSRAM, ROM,
OpenSBI handoff or target boot. They do not prove real FIT parsing across all
configurations, firmware FDT lifetime, maximum stack depth, full 32/64 MiB
PSRAM access, Mbed TLS compatibility, other boards, or sustained operation.
Hardware validation and any diagnostics outside these fixtures remain separate.
