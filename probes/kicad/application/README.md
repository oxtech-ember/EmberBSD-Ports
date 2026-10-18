# KiCad application source port

This directory prepares KiCad 10.0.7 for the common AArch64 GCC16 stack.
It contains source patches, a causal platform regression and cross configuration.
It does not yet provide an accepted KiCad package or GUI workflow.

The [official release announcement](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/)
dates 10.0.7 to 2026-10-07. It is the latest stable release listed by the
[official blog](https://www.kicad.org/blog/) when checked on 2026-10-18.
[sources.tsv](sources.tsv) records the exact archive URL and SHA256.

## Source changes

- `netbsd-platform.patch` selects the existing ELF context implementation
  and `LD_LIBRARY_PATH` branch on NetBSD. It does not change assembly.
- `dxf-major-name.patch` renames the local ellipse vector to `majorAxis`.
  It preserves the system `major()` macro and ellipse calculations.
- `occt8-api.patch` replaces 12 deprecated `GetMessageString()` calls with
  OCCT 8's `what()` API. It preserves the existing exception handlers and
  message lifetimes. KiCad 10.0.7 has no `Standard_Failure::Raise` call.
- `netbsd-proto-macros.patch` keeps the protobuf version accessors valid when
  NetBSD system headers define device macros with the same names. The
  `kiapi` target and its consumers receive a scoped compatibility header.
  Schemas and generated source bytes remain unchanged.

The platform changes adapt pkgsrc `cad/kicad` patches at commit
`fff4deb639a1a640476203c80f752fb77b6cb14b`.
The patch headers name the original revisions and adaptation authorship.
The original KiCad and bundled-library licenses remain in the source tree.
KiCad uses GPL-3.0-or-later; its bundled libcontext uses BSL-1.0.
The new EmberBSD scripts and context contract use BSD-2-Clause and were
written with AI assistance. See [LICENSE](LICENSE).

## Prepare the complete source

Download the archive named in `sources.tsv`. Pass absolute paths:

```sh
./prepare-source.sh /path/to/kicad-10.0.7.tar.bz2 /path/to/new-kicad-source
```

The script verifies SHA256 before creating the source directory.
It refuses an existing output path, including a dangling symlink.
It extracts the full archive and applies all four patches with zero fuzz.
It retains QA data, demos and all application components.
A failed extraction or patch leaves its partial output for inspection.
Use a new output path for another attempt.

## Cross configuration

Prepare a coherent EmberBSD sysroot and its common GCC16 toolchain first.
The toolchain file must select NetBSD/AArch64 and that same sysroot.
Its program search mode must be `NEVER`; library, include and package
search modes must be `ONLY`. Do not use a foreign NetBSD base sysroot.

Set absolute paths for these inputs:

| Variable | Input |
| --- | --- |
| `CC`, `CXX` | Common target GCC16 compilers or wrappers used by the toolchain file |
| `HOST_PYTHON` | Installed native Python 3.15 |
| `HOST_SWIG` | Installed native SWIG 4.5.1 |
| `HOST_PROTOC` | Native protoc from the same upstream release as target Protobuf |
| `TARGET_WX_CONFIG` | Target wxWidgets configuration shell script |
| `PKG_CONFIG` | Target-scoped pkg-config wrapper |

The target Python headers and shared library must be installed under
`/usr/pkg` in the sysroot. Python used by generators runs on the host.
SWIG and protoc also run on the host. The recipe passes target Python
headers, library and site-packages path explicitly to KiCad.
The SWIG gate requires exactly 4.5.1; KiCad 10.0.7's upstream CMake
minimum is 4.0. Passing this version check does not establish compatibility
of the generated Python binding, which still needs its installed tests.
It never executes a target compiler, interpreter or generator in a VM.
Only installed target application tests need the VM.

Select the package profile explicitly:

```sh
KICAD_PROFILE=pkgsrc ./configure-cross.sh \
    /path/to/new-kicad-source /path/to/sysroot \
    /path/to/aarch64.cmake /path/to/new-kicad-build
```

The `pkgsrc` profile preserves the canonical `cad/kicad` choice
`KICAD_SCRIPTING_WXPYTHON=OFF`. That choice is explicit in the pinned
pkgsrc Makefile, revision 1.124 dated 2026-09-02.
It omits Python-created wx interfaces and the wx Python shell.
Core Python embedding, the SWIG `pcbnew` module and IPC stay enabled.
QA, SPICE QA, signal integrity, Wayland and translations stay enabled.
The required wxWidgets components include WebView and GL.
No feature changes in response to a configure failure.

The default `upstream` profile retains KiCad's wxPython `ON` default.
It currently stops before configuration: upstream `FindwxPython.cmake`
imports host wxPython and has no target-query interface.
That profile needs a source fix and real target metadata before acceptance.
The core Python binding still requires independent Python 3.15 compatibility
validation; successful discovery alone is not that validation.

Inspect `ember-logs` after configuration. The script records compiler macros,
generator versions, target package metadata and the actual CMake result.
The [API contract](tests/api/README.md) checks the actual API subdirectory
with matching protobuf 36.2 generation and installed target SDK discovery.
That bounded result does not establish full KiCad configuration.
The install prefix and RPATH contain target paths, not the host sysroot.
Build and stage only after the required dependencies and source adaptations
are complete:

```sh
cmake --build /path/to/new-kicad-build --parallel 2
DESTDIR=/path/to/new-stage cmake --install /path/to/new-kicad-build
```

## Causal platform regression

Use the **pristine** 10.0.7 source, not the patched source directory:

```sh
CXX=/path/to/target-g++ HOST_CXX=/path/to/native-g++ \
    ./platform-regression.rb /path/to/pristine-kicad /path/to/new-regression
```

Both compilers must be GCC16. The target compiler must use the real
EmberBSD sysroot. The script checks the four upstream input hashes.
It reproduces the missing context ABI selection before the patch.
It cross-builds the real libcontext implementation and a lifecycle contract.
The contract performs three context lifecycles and 3003 round trips.
It checks integer messages and floating-point state without `assert`.
The native binary runs locally; `context-target` must run on EmberBSD.
Record its SHA256 and execution result separately from the build receipt.

The DXF and loader regressions preprocess excerpts from the actual source
with real target macros and headers. They are not full translation-unit
builds. The DXF check retains the system macro after the repaired function.
The receipt marks target execution and full KiCad as unrun.
For native Memcheck, compile the contract with `EMBER_VALGRIND` and real
Valgrind headers to register its alternate stacks.

## API source contract

The [actual API harness](tests/api/README.md) builds all 15 upstream schemas
and a separate consumer with common GCC16. It checks version accessors,
known protobuf bytes and descriptor/JSON field names. Native memory checks,
target links and the AArch64 VM contract pass. The harness documents the
analyzer and runtime limits.

## Validation boundary

In the restored environment, the official archive hash, complete source
extraction and zero-fuzz patch application pass. The shell and Ruby syntax
checks pass. Existing-output and wrong-hash preparation controls pass.
The restored GCC16 platform regression passes with fresh pristine inputs
from that archive. The three original ABI, loader and `major()` failures
are reproduced; the patched AArch64 compile, link and preprocessing checks
pass. The native context contract passes all three lifecycles and 3003
round trips. Its alternate-stack Memcheck run has zero errors and no live
allocations, without suppressions. The same AArch64 contract passes in the
EmberBSD VM with the installed GCC16 runtime. The runner's build receipt
retains `target_context_runtime: unrun`; a separate execution receipt records
the exact transferred binary hash and the VM result.

Clang 19 analysis reports no findings in the native libcontext implementation
before or after the patch, or in the repaired target implementation and
the native/target C++ contract. The target baseline fails semantic analysis
for the same missing calling-convention selection as GCC16. Native Cppcheck
2.22 completes with unchanged style findings: twenty in inherited headers
and one const-parameter suggestion in libcontext's existing no-op release
function. The contract has only those twenty header findings. Target
Cppcheck stops while parsing the actual preprocessed system headers
(`setjmp.h` and `stdio.h`); no target Cppcheck-clean result is claimed.
These analyzers do not verify the context-switch assembly itself; the
native memory checks and actual target execution cover the stated contract.

The SWIG 4.5.1 version gate accepts the actual native tool and rejects an
altered 4.4.1 version line. Full KiCad configuration, generated Python-binding
compatibility, installed package tests and the E14 GUI workflows remain
unrun. Earlier private build results are not used as acceptance evidence.
