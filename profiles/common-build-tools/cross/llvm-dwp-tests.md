# LLVM DWP package-index acceptance

The common `llvm-23.1.2nb1` package owns the DWP repair. Its shared LLVM
library, static `LLVMDWP` archive and ordinary `llvm-dwp` tool use the same
source. There is no separate GDB packager dependency. These local fixes and
fixtures are AI-assisted EmberBSD work, not submitted or accepted upstream.

The [canonical patch](../recipes/lang/llvm/patches/patch-lib_DWP_DWP.cpp)
uses each unit's offset width for headers, string offsets and index lengths.
It also reads DWARF4 type-unit headers at their actual width. DWARF5 string
contributions carry individual headers; DWARF4 package contributions obtain
their widths from the indexed CUs. This permits mixed-width inputs and
repackaging while preserving signature-referenced C++ types.
CU and TU indexes can share tables or name independent tables with padding.
String-offset promotion updates their offsets and lengths independently.

The reader checks table lengths, complete entries, string-index bounds and
terminated strings. Invalid metadata returns an error before output is kept.
The validated single-input copy path remains available. String offsets into
valid pooled-string suffixes remain accepted.

## Reproduce

Build fixtures on the development host with the accepted current GCC16
cross compiler and complete target sysroot:

```sh
export EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK
python3 -B profiles/common-build-tools/cross/build-llvm-dwp-tests.py \
    /absolute/gcc16/bin/aarch64--netbsd-gcc /absolute/sysroot \
    /absolute/new-fixtures
```

The compiler's installed tool layout must support `-gsplit-dwarf`. The
Python builder changes only the generated section copies. Transfer the fixtures and target runner without AppleDouble
files, using `COPYFILE_DISABLE=1 tar --no-xattrs` on macOS. The original
absolute build directory must not exist on the target.

Run with the ordinary installed packages on NetBSD 11/AArch64:

```sh
sh run-llvm-dwp-tests.sh /usr/pkg/bin/llvm-dwp /usr/pkg/bin/gdb \
    /absolute/fixtures /absolute/new-results
```

The runner also forces DWARF5 string-offset promotion during repackaging.
For the indexed-layout gate, return the result directory to the host and
create legal padding, shared TU tables and independent TU contributions:

```sh
CC=/absolute/gcc16/bin/aarch64--netbsd-gcc \
OBJCOPY=/absolute/gcc16/bin/aarch64--netbsd-objcopy \
    python3 -B profiles/common-build-tools/cross/prepare-llvm-dwp-index-tests.py \
    /absolute/results /absolute/fixtures /absolute/new-indexed-fixtures
```

Transfer that directory and run the same target runner with fresh results.
Its empty ELF input forces the multi-input writer without adding another CU.

For pre-installation validation only, `LLVM_LIBRARY_PATH` may select the
matching staged LLVM library. The runner applies it solely to `llvm-dwp`;
GDB uses its normal loader environment. The runner bounds CPU, virtual
memory and output size, requires malformed inputs to return status 1, and
rejects any retained output from a failed packaging attempt.

The source gate checks the pinned upstream archive, patch checksum,
zero-fuzz application, rejection of repeated application and recipe ownership:

```sh
sh profiles/common-build-tools/tests/llvm-dwp-source.sh \
    /absolute/llvm-project-23.1.3.src.tar.xz /absolute/new-source-check
```

The source gate also passes on 23.1.3. The runtime matrix below records the
previous accepted package; it must be repeated for the replacement library.

## Matrix and evidence

On 2026-10-08, the normally installed `llvm-23.1.2nb1` package passed these
104 checks in the AArch64 UTM VM with GDB 18.1 and Binutils 2.47, without
loader overrides:

| Cases | Count | Required observation |
| --- | ---: | --- |
| DWARF4/5, 32/32, 64/64, 32/64, 64/32, plain and type-unit inputs | 40 | Direct and repacked two-CU indexes, plus forced DWARF5 promotion; GDB reads values in both CUs, record members and normal exit without standalone DWO fallback |
| Indexed padding, shared and independent TU string tables | 40 | The same live workflow after multi-input rewriting, repackaging and DWARF5 promotion |
| Truncated headers/entries/units, excessive lengths, invalid string offsets, unterminated strings, maximum and truncated strx operands in both widths | 22 | Single and two-input packaging return 1, bounded diagnostic, no retained package |
| String suffix offsets | 2 | Valid single and two-input packages |

Unmodified LLVM 23.1.2 failed all twelve initial DWARF64/mixed input
combinations; the four DWARF32 combinations packaged successfully. The
earlier fixture-only repair produced corrupt DWARF4/64 type-unit indexes.
Its mixed-width repack could loop when a table read stopped advancing.
The retained tests exercise these causes through the common package.

Normal pkgsrc PLIST, interpreter, dependency, PIE, RELRO, RPATH and
work-directory checks passed. The two inherited opt-viewer permission
warnings remain. Installed `pkg_admin check llvm` verified 2,789 files.
The unchanged [C API/bitcode and ORC consumers](llvm-api-tests.md) also
passed four default JITLink/RTTI lifecycles and the expected missing-symbol
failure against the installed shared library.

The incremental build reused the accepted 23.1.2 static component archives.
As a control, the exact CMake link command reproduced the original stripped
shared library byte for byte. Replacing the rebuilt DWP object changed only
`lib/libLLVMDWP.a` and `lib/libLLVM.so.23.1` among the 2,789 payload entries.
Pkgsrc regenerated metadata and packaged the checked stage.

| Artifact | SHA256 |
| --- | --- |
| `llvm-23.1.2nb1.tgz` | `e677db8bb4a579fc697651025ad3cbdcb27345f56a062f64cac88ac3d259397c` |
| Installed `libLLVM.so.23.1` | `59486085a768044e0f1940a067f24be4149c420078ae496972bbea303b7b2eb7` |
| `libLLVMDWP.a` | `7de325e0e9d3b1247a5e370e4d3f540d62f8218a50d6cee6e0b6a0a2aa1a1bbe` |
| Original and reproduced baseline `libLLVM.so.23.1` | `42231ed6dbaf213a3a391dff50eb51986b0c8fbb8cff8821c42fa07fbc84b1e6` |

This is focused package and live-debugger evidence. It does not establish
big-endian producers, contributions above 4 GiB, skeletonless type units,
or universal DWARF
conformance. The package revision does not change the upstream LLVM version
reported by `llvm-config` or the shared-library ABI.
