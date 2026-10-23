# Compose the complete graphics cross profile

Use the prepared `common-graphics` export and the accepted
[common cross tools](../../common-build-tools/cross/README.md). The cross
composition consumes the same canonical GCC16/Python3.15/Meson1.12.1/LLVM23
package family. It does not include the native common-tools `mk.conf`, which
selects an installed native compiler and rejects cross builds.

A private MAKECONF extends the existing common cross MAKECONF:

```make
.include "/absolute/common-cross.mk.conf"
.if defined(BSD_PKG_MK)
WRKOBJDIR=/absolute/new-graphics-work
EMBERBSD_COMMON_GRAPHICS_CROSS=yes
EMBERBSD_GRAPHICS_LLVM_CONFIG=/absolute/llvm-metadata-tool/bin/llvm-config
EMBERBSD_WAYLAND_SCANNER=/absolute/scanner-work/prefix/bin/wayland-scanner
.include "/absolute/prepared-pkgsrc/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
.endif
```

The common MAKECONF supplies the host bootstrap configuration, existing cross
compiler, target sysroot and host prefix. `CROSS_LOCALBASE` remains `/usr/pkg`;
pkgsrc retains the separate host `TOOLBASE`. This distinction matters because
MAKECONF is read before pkgsrc replaces the host `LOCALBASE` with the target
value. Cross graphics selects modular X11 dependencies in the target sysroot.
The native graphics profile retains its existing compiler and X11 policy.
When pkgsrc recursively builds a native tool dependency, it reuses MAKECONF
with `USE_CROSS_COMPILE=no`. The opted-in cross graphics profile leaves those
host builds and their dependencies to the host configuration. It does not
apply target platform, prefix or graphics-provider checks to host Mako or
MarkupSafe. The ordinary native graphics profile remains strict.

For cross libX11, the profile also binds `NATIVE_CC` to the common profile's
absolute `EMBERBSD_CROSS_BUILD_CC`. The pkgsrc recipe appends its own
`CC_FOR_BUILD` assignment. Its empty Darwin default otherwise clears the host
compiler selection, and upstream finds the target `gcc` wrapper for `makekeys`.
The generator must run on the build host while reading target xorgproto headers.
Cross libxshmfence exposes the already selected host `libtoolize` through
pkgsrc's tool creation mechanism. The pinned pkgsrc has no `USE_TOOLS`
mapping for that program, and its cross PATH excludes `TOOLBASE/bin`.
The recipe's real `autoreconf` therefore needs this scoped tool declaration.

CMake dependencies also receive the NetBSD system/processor and sysroot.
Their library, include and package searches are confined to the sysroot and
buildlink tree; program searches use the build host. This prevents packages
such as libepoll-shim from configuring as Darwin and adding `-arch arm64` to
the NetBSD compiler command. The common cross-tools profile remains unchanged.
libepoll-shim also runs a zero-timeout kqueue probe. Supply
`EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=0` or `1` from that probe on the selected
target; absence or another value fails. The profile forwards the measured
status to CMake and never guesses the target's kernel behavior.

Build the [LLVM metadata helper](llvm-config.md) only after LLVM's target
metadata is free of build-path leaks. For complete Mesa configuration, its
prefix must be the actual LLVM installation in `CROSS_DESTDIR/usr/pkg`.
Canonical real paths must agree between the common MAKECONF and helper input.
The recipe verifies the helper's hash receipt independently before invoking
it, then checks target triple, prefix/header/library directories, version,
RTTI and shared ORC/native components. It does not run a target ELF tool on
the build host or accept the native generator build's host metadata.

Both graphics recipes use pkgsrc's `TOOL_PYTHONBIN`, including libdrm's
build-script shebangs. `PYTHONBIN` continues to describe the target interpreter.
Their pre-configure guards require the selected Python 3.15 host interpreter.
Mesa also requires its real Mako, packaging and YAML imports.
`tests/python-host-guards.rb HOST_PYTHON315 OLDER_HOST_PYTHON NEW_WORK` runs
both production guards. Its older-interpreter controls test the exact version
predicates without requiring obsolete module installations.
Mesa substitutes that exact host executable into its existing interpreter
list; its real version/import checks remain active. Libdrm's Python entry and
Mesa's LLVM entry are emitted by pkgsrc into the actual Meson cross file.
The cross recipe also records the target `nm` there, so all five ELF ABI
checks select the explicit cross tool. Native recipes retain their normal
tool search.
No cross-file response stub or fallback package provider is introduced.

Mesa cross builds require native Flex at `${TOOLBASE}/bin/flex`, satisfying
pkgsrc's `FLEX_REQD`. Missing, unrelated or older executables fail before
configuration. All six upstream Mesa lexers handle `yywrap` themselves, so
source generation does not require target libfl. Native package policy is
unchanged. From this profile directory, run with actual bmake available
through `BMAKE` or `PATH`:

```sh
"$HOST_PYTHON315" tests/mesa-native-flex.py \
  PKGSRC MAKECONF MESA_ARCHIVE NEW_WORK
```

This checks real dependency routing, native policy, three provider refusals,
the pinned source archive and native generation of all six lexers.

Build the matching scanner with [build-wayland-scanner.sh](build-wayland-scanner.sh).
Select its `prefix/bin/wayland-scanner` through `EMBERBSD_WAYLAND_SCANNER`.
Mesa and protocols require the helper's real installed `wayland-scanner.pc`
and `installed.sha256`. Before configuring they verify the installed payload,
the scanner version, and the metadata's prefix and executable path.
Mesa additionally checks the target Wayland client version is exactly 1.26.0.
Use a fresh work directory when changing the selected host tools.

The consumer recipes emit a separate native Meson file. Its pkg-config reads
the scanner prefix and host `TOOLBASE`, with the inherited target sysroot
cleared. Target dependencies still use the cross buildlink configuration.
This matters for protocols: upstream 1.49 silently omits all enum headers
when native scanner metadata is missing, even if a scanner binary is supplied.
The cross-file binary entry alone does not provide that metadata.

## Prerequisites and remaining acceptance

The sysroot needs the selected target libdrm, zstd/zlib, expat, libudev-bsd,
Wayland 1.26.0nb2, protocols 1.49 and modular X11 dependencies. The matching host
scanner is a build tool. It does not install a second target Wayland provider.

The [Linux/GCC16 receipt](mesa-linux-aarch64.md) passes full Mesa packaging,
installed llvmpipe rendering and all 39 target invocations in E34 VM.
For another stack, use ordinary pkgsrc build, `check-files`, package and
WRKREF checks after staging the dependencies. Run target LLVM/Mesa
API and ORC tests, then rebuild GLU, libepoxy, Qt/Wayland, compositor and other
installed graphics consumers against the same canonical provider. Inspect
loaded plugins as well as direct ELF dependencies. Do not substitute SONAME
links for rebuilding consumers of base GL3/EGL0/DRM3 or old libglapi.

The AArch64 Mesa package always contains the [PowerVR ICD](powervr.md),
a real Vulkan provider. The amd64 package has no Vulkan ICD. AArch64 requires sealed native
Mesa generators and separate loader/ICD runtime acceptance. Existing llvmpipe
acceptance does not establish Vulkan or hardware acceleration.

## Source-causal checks

The profile validates the final pkgsrc target when `PKG_FAIL_REASON` expands.
`MAKECONF` runs before `bsd.prefs.mk` replaces the host `MACHINE_ARCH`.
An early comparison can reject amd64 on an AArch64 build host.
The deferred checks still reject unsupported platforms and mismatched targets.

On an AArch64 Darwin host, test this phase with a prepared amd64 MAKECONF:

```sh
BMAKE=/absolute/host/bin/bmake ruby ../tests/cross-makeconf-phase.rb \
    /absolute/prepared-pkgsrc /absolute/amd64-cross.mk.conf /absolute/new-phase-work
```

This reads a real pkgconf recipe and exercises pkgsrc's normal failure gate.
It does not build or execute target packages.
The AArch64 case checks target metadata; it does not supply missing ARM inputs.

Use real prepared recipes and existing cross tools; these checks build no
package or dependency:

```sh
BMAKE=/absolute/host/bin/bmake ruby ../tests/cross-selection.rb \
    /absolute/prepared-pkgsrc /absolute/common-cross.mk.conf \
    /absolute/llvm-metadata-tool/bin/llvm-config \
    /absolute/scanner-work/prefix/bin/wayland-scanner /absolute/new-test-work
BMAKE=/absolute/host/bin/bmake TEST_CMAKE=/absolute/host/bin/cmake \
    ruby ../tests/cmake-cross.rb /absolute/prepared-pkgsrc \
    /absolute/common-cross.mk.conf /absolute/new-cmake-test-work
```

The regression parses the complete recipes, generates pkgsrc's actual Meson
machine files and exercises the production receipt verifier. It checks native
profile preservation separately through `../tests/profile.sh`. The cross
parser accepts the selected tool while refusing absent opt-in, wrong paths,
provider overrides and altered helper bytes. A successful parse does not
bypass the later requirement for a complete shared LLVM payload.

The CMake regression uses the actual libepoll-shim recipe's emitted arguments.
On macOS/AArch64, an unconfigured control selects Darwin; the production flags
select NetBSD/AArch64 and find real target headers/libraries separately from
host programs. Both valid explicit timer statuses pass through unchanged;
missing and invalid statuses fail before configuration. This checks cache
selection, not the target kernel probe itself.

After preparing the canonical Mesa source and configuring its real pkgsrc
build, the SSP regression compiles the original and patched colour-matrix TU
with the actual compile command and pkgsrc wrapper. The original must fail
at fortified `memcpy`; the patched ELF must retain `_FORTIFY_SOURCE=2` and
the macro. The nm regression then inspects all five real ABI test commands
and decodes the resulting AArch64 object with the selected cross tool:

```sh
ruby ../tests/mesa-ssp.rb /absolute/mesa-26.2.4.tar.xz \
    /absolute/pkgsrc-work/mesa-26.2.4/output /absolute/new-ssp-test-work
ruby ../tests/mesa-cross-nm.rb /absolute/pkgsrc-work/mesa-26.2.4/output \
    /absolute/cross-tools/bin/aarch64--netbsd-nm \
    /absolute/new-ssp-test-work/patched.o /absolute/new-nm-test-work
```

The libX11 regression uses the complete composed cross MAKECONF and verified
upstream libX11 source. It checks the last real `CC_FOR_BUILD` assignment,
native dependency preservation, then compiles and runs upstream `makekeys`
against the actual target xorgproto headers:

```sh
BMAKE=/absolute/host/bin/bmake ruby ../tests/x11-makekeys.rb \
    /absolute/prepared-pkgsrc /absolute/graphics-cross.mk.conf \
    /absolute/libX11-1.8.13 /absolute/new-makekeys-test-work
```

For libxshmfence, the focused regression generates the actual pkgsrc tools
and runs upstream `autoreconf -vif` on a private copy of the prepared source.
It preserves the cross PATH and checks that native recursion stays unchanged:

```sh
BMAKE=/absolute/host/bin/bmake ruby ../tests/x11-autoreconf.rb \
    /absolute/prepared-pkgsrc /absolute/graphics-cross.mk.conf \
    /absolute/libxshmfence-1.3.3 /absolute/new-autoreconf-test-work
```

For scanner consumers, supply the verified patched upstream source trees:

```sh
BMAKE=/absolute/host/bin/bmake TEST_PYTHON=/absolute/host/bin/python3.15 \
TEST_MESON=/absolute/meson.py NINJA=/absolute/host/bin/ninja \
ruby ../tests/scanner-consumers.rb /absolute/prepared-pkgsrc \
    /absolute/common-cross.mk.conf /absolute/llvm-metadata-tool/bin/llvm-config \
    /absolute/scanner-work/prefix/bin/wayland-scanner \
    /absolute/wayland-protocols-1.49 /absolute/mesa-26.2.4 /absolute/new-scanner-tests
```

This regression runs upstream protocol configuration and generation, checks
the complete enum-header PLIST, and executes Mesa's actual Wayland module
call. Its control demonstrates omitted headers without native metadata.
Production guards reject altered executable bytes and inconsistent metadata.
No target library or package is built by this check.
