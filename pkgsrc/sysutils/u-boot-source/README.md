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

## Host regression checks

The scripts in `tests/` use an explicitly prepared U-Boot source tree and a
native Ports prefix containing Clang/LLD, Python, libfdt and, for the FIT hash
check, OpenSSL. Run them with the prefix Python. For example, with `SOURCE`
and `HOST_PREFIX` set to those directories:

```sh
for check in test-sha256.py test-spl-strings.py test-fit-flow.py \
    test-fit-read.py test-fit-hash.py test-psram-layout.py test-reserve.py test-s31-mpll.py \
    test-mips-endian.py test-prof-align.py test-env-awk.py; do
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
