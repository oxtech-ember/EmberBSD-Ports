# Build the native Darwin toolchain

Clang and LLVM are the default native toolchain. GCC remains an explicit
choice through `EMBERBSD_COMPILER_FAMILY=gcc` for a platform that needs it.
Both routes use the same shared Ports recipes and native package prefix.
A compiler selection does not change the target C or C++ runtime ABI.

## First tools

Export the pinned pkgsrc tree with the root [source command](../../README.md#package-integration).
Source preparation needs an existing control Python, Git, and patch.
It does not require a completed SDK.

The exported `bootstrap/bootstrap` supports `--compiler clang`,
`--unprivileged`, `--prefix`, `--pkgdbdir`, `--workdir`, and `--mk-fragment`.
Declare the initial compiler, its native ABI, shell, and auxiliary host tools.
On macOS, a declared Apple Clang and Command Line Tools installation can build
this first prefix. An official native LLVM installation is another initial
provider. These tools are bootstrap inputs, not the final native SDK.
Keep bootstrap objects, package state, and installed files in the selected
workspace. Do not install a host package manager as an implicit fallback.

Pass complete `CC`, `CXX`, and `CPP` commands to bootstrap. Set `CLANGBASE`
to the selected initial Clang installation. Set the native SDK and deployment
arguments explicitly. The mk fragment must retain the same compiler and ABI
for the package builds that bootstrap starts. Keep inherited compiler and make
flags out of the invocation. Read the actual bootstrap help before execution.

Set `SDKROOT` to the absolute native SDK directory. The exported bootstrap
keeps this directory even when the deployment target names a different release.
It writes the directory as `OSX_SDK_PATH` to the bootstrap and installed
mk.conf files, so package builds use the same SDK.
It rejects missing headers or libraries instead of selecting another SDK.
The path uses bootstrap's supported letters, digits, `-`, `_`, `.`, and `/`.
Without `SDKROOT`, the upstream SDK discovery behavior remains available.
`tests/bootstrap-sdkroot.py --bootstrap PATH --shell PATH` executes this
selection and mk.conf logic without compiling; run it from this profile directory.

Build the final Clang, LLVM, LLD, shell, Python, make, and required utilities
from the exported shared recipes. After the native prefix supplies the needed
roles, use [native tool selection](../common-build-tools/cross/native-toolset.md).
The final build PATH and compiler components stay inside that prefix.
Native macOS ABI headers and libraries remain explicit host inputs.

The native package profile forwards its selected `OSX_SDK_PATH` as `SDKROOT`
through pkgsrc's `ALL_ENV` to configure, build and test phases. Rust needs this
ABI input before invoking the selected linker; without it, rustc attempts Apple
SDK discovery even when the C compiler already has explicit `-isysroot` flags.
The profile remains native-only and does not change cross host/target selection.
`tests/darwin-rust-sdkroot.py --help` describes the actual pkgsrc/Cargo regression:
no inherited SDKROOT, a deliberately conflicting inherited value, and removing
only the binding must reproduce rustc's attempted `xcrun` discovery.

When the native dependency closure needs gettext tools and the prefix does not
already contain a compatible full `style` package, prepare gettext before
building the remaining closure. Use the same selected bmake, MAKECONF, PATH,
prefix and package database as the rest of the bootstrap. The common
[gettext bootstrap composition](../common-build-tools/gettext-bootstrap.md)
keeps the plain and full variants at the same package identity. For a fresh
prefix, the concrete sequence is:

```sh
PKGSRC_MAKE=/absolute/host-prefix/bin/bmake
PKGSRC_MKCONF=/absolute/bootstrap-work/mk.conf
PKGSRC_ADD=/absolute/selected-pkg-add
"$PKGSRC_MAKE" -m /absolute/host-prefix/share/mk \
  MAKECONF="$PKGSRC_MKCONF" EMBERBSD_DARWIN_BOOTSTRAP=yes \
  -C /absolute/pkgsrc/devel/gettext-tools \
  WRKOBJDIR=/absolute/common-objects/gettext-plain \
  PACKAGES=/absolute/common-objects/gettext-plain-packages \
  PKG_OPTIONS.gettext-tools=-style package
"$PKGSRC_ADD" -K /absolute/host-prefix/pkgdb -u \
  /absolute/common-objects/gettext-plain-packages/All/gettext-tools-1.0nb7.tgz
"$PKGSRC_MAKE" -m /absolute/host-prefix/share/mk \
  MAKECONF="$PKGSRC_MKCONF" EMBERBSD_DARWIN_BOOTSTRAP=yes \
  -C /absolute/pkgsrc/devel/glib2 \
  EMBERBSD_BUILD_MSGFMT=/absolute/host-prefix/bin/msgfmt \
  TOOLS_PLATFORM.xgettext=/absolute/host-prefix/bin/xgettext build install
"$PKGSRC_MAKE" -m /absolute/host-prefix/share/mk \
  MAKECONF="$PKGSRC_MKCONF" EMBERBSD_DARWIN_BOOTSTRAP=yes \
  -C /absolute/pkgsrc/textproc/libcroco \
  EMBERBSD_BUILD_MSGFMT=/absolute/host-prefix/bin/msgfmt \
  TOOLS_PLATFORM.xgettext=/absolute/host-prefix/bin/xgettext build install
"$PKGSRC_MAKE" -m /absolute/host-prefix/share/mk \
  MAKECONF="$PKGSRC_MKCONF" EMBERBSD_DARWIN_BOOTSTRAP=yes \
  -C /absolute/pkgsrc/devel/gettext-tools \
  WRKOBJDIR=/absolute/common-objects/gettext-full \
  PACKAGES=/absolute/common-objects/gettext-full-packages \
  EMBERBSD_BUILD_MSGFMT=/absolute/host-prefix/bin/msgfmt \
  TOOLS_PLATFORM.xgettext=/absolute/host-prefix/bin/xgettext \
  PKG_OPTIONS.gettext-tools=style package
"$PKGSRC_ADD" -K /absolute/host-prefix/pkgdb -U \
  /absolute/common-objects/gettext-full-packages/All/gettext-tools-1.0nb7.tgz
```

The selected `PKGSRC_ADD` is the explicit `pkg_add` tool supplied to the SDK
renderer; it can come from the initial tool roots before the final package tools
are installed. The ordinary pkgsrc dependency handling prepares any missing prerequisites. Verify the final
package with the selected `pkg_info -Q PKG_OPTIONS` and reuse the installed
full package when its version and `style` option already satisfy the recipe.
An existing prefix whose consumers use libtextstyle must keep its full package:
reuse its compatible gettext tools while preparing GLib and libcroco, then build
and install the full package directly. Do not replace it with the plain variant.

## Explicit Darwin package profile

The exporter installs [darwin-bootstrap.mk.conf](darwin-bootstrap.mk.conf) as
`EMBERBSD-DARWIN-BOOTSTRAP-MK.CONF`. The SDK's
[Darwin renderer](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/darwin-bootstrap.md)
creates its ordinary MAKECONF and complete make invocation.
It supplies paths, host facts, and command arguments. This is configuration,
not an admission report or a second package manager.

| Input | Meaning |
| --- | --- |
| `EMBERBSD_COMPILER_FAMILY` | `clang` by default, or explicit `gcc` |
| `EMBERBSD_DARWIN_SEED_CC`, `CXX`, `CPP`, `AS` | Complete selected compiler and assembler commands |
| `EMBERBSD_DARWIN_LD64_LLD`, `DSYMUTIL`, `AR`, `RANLIB`, `NM`, `STRIP` | Explicit native linker and archive/symbol tools |
| `EMBERBSD_DARWIN_SDK_VERSION`, `OSX_SDK_PATH` | Native ABI metadata and directory |
| `EMBERBSD_DARWIN_HOST_*` | Actual host OS, CPU, kernel, product and pkgsrc OS versions |
| `EMBERBSD_DARWIN_MAKE`, `GMAKE`, `SH` | Complete make commands and the selected shell |
| `EMBERBSD_DARWIN_NATIVE_TOOLS`, `TOOL.name` | Explicit utility names and executable paths |
| `EMBERBSD_DARWIN_SOURCE_TOOLS` | Utilities to build through their common recipe dependencies |
| `EMBERBSD_DARWIN_JOBS`, `CPU_BUDGET` | Jobs and the coordinator's available CPU budget |
| `WRKOBJDIR`, `DISTDIR`, `PACKAGES`, `LOCALBASE`, `PKG_DBDIR` | Selected work, cache, output, and package database paths |

Names abbreviated after a comma retain the preceding `EMBERBSD_DARWIN_`
prefix. Initial `LLVM_MC` remains a declared assembler backend path;
`SEED_AS` is the actual command. Clang uses its integrated assembler through
`clang -c -x assembler`, with the selected native ABI arguments.
The installed Clang package supplies `bin/clang-as` for APIs that accept only
one executable path. This entry point executes the same prefix's Clang and
mksh. It does not search PATH or replace a missing compiler.

The profile selects the ordinary unprivileged pkgsrc install policy.
It does not modify system users or `/etc/shells`. Native package checks,
checksums, and required-library checks remain enabled.
The profile includes `EMBERBSD-DEFAULTS-MK.CONF` on the later MAKECONF read,
which has `PKGPATH`. Native bootstrap builds thus accept the shared licenses.
They also reject any version of a versioned family other than the kept one.
The profile does not require the `od`, `lipo` and `otool` roles of the Mach-O
load-command checker. The defaults do not turn that checker on here, so pkgsrc
uses its default Mach-O requirement detection. A recipe that turns the checker
on before `bsd.prefs.mk` keeps it.
The initial ordinary bootstrap omits the optional builtin helper from its PLIST.
`tests/bootstrap-mk-plist.py` checks this selection with an exported tree,
the selected make executable, and an ordinary bootstrap MAKECONF.

The compiler wrappers retain each selected command tail once. The Clang route
uses separate `as` and `cpp` role aliases even when all three commands select
the same Clang executable. Both wrapper backends keep the absolute driver
separate from its arguments, including commands without a tail. The Clang route
does not receive GCC's static libstdc++, libgcc, or default-RPATH flags.
The explicit GCC route accepts its earlier `EMBERBSD_GCC16_*` input names and
retains the GCC Darwin recipe's driver routing and runtime options.
Missing tools and invalid families fail; neither route silently chooses the other.

The [make handoff](../common-build-tools/bootstrap/README.md#make-handoff)
keeps the initial make and shell only for their bootstrap closure. Later
packages use the installed bmake, makefiles, and mksh. Gzip has its separate
source dependency closure. No receipt or repeated bootstrap is needed to use
working compatible tools.

## Checks and remaining scope

The compiler-family fixture evaluates the actual make policy and wrapper
fragment. It checks Clang defaults, explicit GCC compatibility, exact command
arguments, missing inputs, invalid families, and unchanged ordinary branches.
It also checks the shared defaults with two MAKECONF reads, as
`mk/bsd.prefs.mk` does. A removed `lang/python314` is rejected and
`lang/python315` is accepted. The shared licenses keep the pkgsrc default
license list. The Mach-O checker stays off unless a recipe turns it on.
Native adapter checks cover compiler-family forwarding, assembler arguments,
prefix paths, and stale configuration refusal. The `clang-as` fixture checks
argument preservation, child exit statuses, and missing-compiler refusal.
These checks do not claim a completed LLVM package or target runtime.

[`tests/darwin-clang-wrappers.py`](tests/darwin-clang-wrappers.py) generates
both real wrapper backends from a current Ports export (`--pkgsrc`). Pass
each member of the complete Darwin bootstrap make command with `--make-arg`,
the native cwrappers directory with `--cwrappers-dir`, and a new `--work`
directory. It compiles, assembles, preprocesses, links and runs small native
C/C++ consumers, checking the executed driver and exact argument tails.
The test reads the libnbcompat recipe and keeps all output under `--work`;
it does not build or install packages.

Clang's installed default linker is LLD from the same package prefix.
Verify actual C and C++ driver commands, installed compile/link/run behavior,
and loaded native runtime libraries after building the native package.
A NetBSD target additionally needs the prepared common LLVM runtime and CRT
contract. An existing GCC runtime or Apple's native libc++ does not establish
that target contract.
