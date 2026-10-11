# Accept the installed common Mesa package

Current nb3 also passes [physical CM5 V3D acceptance](mesa-cm5.md),
including 1280x800 render targets. The earlier CPU receipts below remain
scoped to their original versions and hardware.

Build `graphics/MesaLib` with the [complete cross composition](profile.md),
the accepted GCC16 toolchain and installed shared LLVM23. Use normal pkgsrc
`package` and `install` targets. Keep the source, recipes, MAKECONF and tools
unchanged while a build is running. Preserve compiler output, Meson metadata,
the final package and their input hashes; do not replace a complete build log
with incremental output.

pkgsrc's normal `install-check-version` compares the extraction cookie with
the current package name, including `PKGREVISION`. A revision bump can trigger
automatic cleaning and rebuilding of the existing work directory. Preserve
the accepted package, tests and receipts first; do not assume an incremental
restage will retain old objects, and do not disable this stale-work check.
This occurred during the nb1-to-nb2 metadata correction; the second package
therefore uses a fresh Mesa build rather than repackaged old build objects.

On 2026-10-08, Apple Silicon macOS/GCC16 cross-built MesaLib 26.2.4nb1 with
VirGL, softpipe, llvmpipe/shared LLVM23 ORC, X11/Wayland, EGL, GL/GLES and GBM.
Normal package file, permission, PIE/RELRO, RPATH and work-reference checks
passed, followed by installation in the target sysroot. The actual payload
matched the canonical PLIST. Eight host tests passed: the NIR algebraic
parser, EGL entrypoints, drirc XML validation and five target-ELF ABI checks.

The installed package then passed surfaceless rendering on Orange Pi Zero 3W
(Allwinner A733): four shader/triangle/EGL lifecycles reported EGL 1.5,
GLES 3.2 and llvmpipe with LLVM 23.1.2, 128-bit vectors. All 37 upstream test
invocations exited zero, including the seven llvmpipe JIT tests. XML
configuration passed all 15 cases. Utility tests passed 253 cases and skipped
`Cache.List` because dynamic Foz lists are unsupported; NIR passed 6197 cases
and reported nine upstream-disabled tests. The negative expected-VirGL check
rejected the actual llvmpipe renderer. Runtime used the installed package
closure, without private libraries or loader overrides.

Revision nb2 corrects the private X11 requirement in `gl.pc`, `glx.pc` and
`egl.pc` from `xfixes` to Mesa's actual `xcb-xfixes` dependency. The associated
buildlink recipe drops unused Xlib Xdamage/Xfixes requirements. A fresh full
pkgsrc build passes normal package checks; all eight ELF files and every
symlink remain byte-identical to nb1. Only those three metadata files change.
The compiler commands are byte-identical; Meson's option objects also match
(their JSON array order changed during fresh configuration).

Before the correction, the installed package's actual pkg-config lookup failed
on missing `xfixes`. After normal sysroot upgrade, this regression checks all
seven modules, including private requirements, and compiles the pixel consumer:

```sh
ruby ../tests/mesa-pkgconfig.rb /absolute/cross-tools /absolute/sysroot \
    /absolute/host/bin/pkg-config /absolute/new-metadata-test-work
```

Static metadata queries do not claim that static Mesa libraries were built.
The resulting target ELF still requires target execution. Retain nb1's accepted
package and target evidence; identical ELF hashes permit a short installed
payload/renderer check for this metadata update without repeating all 37 runs.
Normal nb2 installation on Zero 3W passes its complete file/link/runtime
manifest and four direct EGL shader/pixel lifecycles. The subsequent
[libepoxy consumer](epoxy.md) also passes installed dynamic dispatch and its
four selected upstream invocations against that same Mesa package.

The build uses the sysroot's NetBSD zlib 1.3.1 alongside common expat 2.8.5,
zstd 1.5.7 and LLVM 23.1.2. Vulkan drivers, Rusticl and Teflon are outside this
classic graphics recipe. The earlier [softpipe diagnostic](README.md#temporary-headless-mesa-diagnostic)
is a separate, temporary uninstalled result.

## Prepare target tests

After installing the real package into the matching sysroot, run:

```sh
ruby prepare-mesa-package-tests.rb /absolute/cross-tools /absolute/sysroot \
    /absolute/prepared-mesa-26.2.4 /absolute/mesa-build \
    /absolute/MesaLib-26.2.4nb3.tgz /absolute/new-acceptance-work
```

The helper compiles the existing EGL/GLES pixel consumer against installed
headers and libraries. It copies the 38 target ELF invocations declared by
the actual Meson build, including seven llvmpipe JIT tests and the V3D QPU disassembler test. It preserves
upstream's test timeouts and XML configuration fixtures, including `.drirc`.
It records tool, build-metadata, test-binary, package and library hashes.
Every installed Mesa file/symlink is compared with the original package.
Target `readelf` recursively inspects dependencies of all Mesa modules and
test binaries. Noncanonical runtime paths or unresolved target libraries fail.

`mesa-package-tests.tar.gz` contains executables, fixtures, the runner and
receipts. It contains no private runtime libraries. The runtime manifest
records every resolved `/usr/pkg` library path and its exact SHA256, including
SONAME aliases. Base libraries retain the target OS's ownership. Install the
matching normal packages and dependencies on the target before testing.
The helper does not install packages, change a desktop or deploy to a board.

The host-only integrity regression checks the original complete bundle and
sysroot. It rejects changes to the real ELF consumer, library manifest and
hidden XML fixture before platform inspection, `ldd` or target execution.
An isolated file fixture also proves rejection of installed drirc drift and
a changed symlink whose resolved bytes still match. Hard links save space;
the fixture replaces its config link before writing, preserving the sysroot.

```sh
ruby ../tests/mesa-package-bundle.rb /absolute/new-acceptance-work/bundle /absolute/sysroot \
    /absolute/new-integrity-work
ruby ../tests/mesa-package-loop.rb ./run-mesa-package-tests.sh \
    /absolute/new-loop-test-work
```

`run-mesa-package-tests.sh --verify-sysroot BUNDLE SYSROOT` performs only
these filesystem checks. It does not report target runtime success.
The second regression executes the production loader function and test loop
with labelled host shell fixtures. It catches accidental replacement of a
relative test basename by an absolute path inside the loader function.

## Run on NetBSD/AArch64

Verify the archive SHA256 after transfer and extract it into a new private
directory. NetBSD/AArch64, a baseline ARMv8 CPU and `/usr/bin/timeout` are
required. LLVM detects the target CPU for JIT code. No DRM device, display
server or physical GPU is needed for this surfaceless CPU-rendering check.

```sh
sh /absolute/bundle/run-mesa-package-tests.sh \
    /absolute/bundle /absolute/new-target-logs llvmpipe
```

The runner verifies every bundle artifact, all installed Mesa payload hashes,
exact Mesa symlink targets and installed library hashes before
executing target code. `ldd` must resolve package dependencies to recorded
`/usr/pkg` files; only base `/usr/lib` and `/lib` are allowed otherwise.
Loader and driver overrides are rejected. Each test child receives a clean
environment. Only the XML test receives `HOME` pointing to upstream's actual
fixture home and `DRIRC_CONFIGDIR`; the user's home is neither changed nor
used as a temporary variable. Process-name tests receive the relocated
absolute executable path matching their upstream contract.

The render consumer rejects invalid GLSL, draws and reads triangle pixels,
checks the llvmpipe renderer name and repeats four EGL lifecycles. It has a
60-second limit. Upstream test limits are 30, 120, 180 or 240 seconds.
`TIMEOUT` can select another absolute target timeout executable. Logs preserve
loader paths, test output and OS identity. Process exit 77 is reported as a
skip; internal GTest skips and disabled tests are reported separately from
successful process exits. A complete run does not prove a visible X11 or
Wayland session, VirGL acceleration, physical GPU support or long-run stability.

For a negative renderer check, use `virgl` as the expected name on the same
surfaceless CPU path. This must fail with `unexpected renderer`, not timeout
or loader failure. Preserve the failed run separately from the positive run.
