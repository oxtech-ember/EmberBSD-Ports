# Bind the initial make shell

An initial make binary can have external system-makefile and shell paths
compiled into it. Copying that binary does not change these paths.
The fixed selector `ports-bootstrap-make-v1` binds explicit makefiles and a
selected POSIX shell for a bounded bootstrap producer.
It does not qualify the input binaries as an ordinary native toolset.

## Inputs and layout

The SDK owns input admission, bundle assembly and the producer plan.
It must pin the make binary, its package metadata, the complete upstream
makefile tree and its source provenance. Keep historical builders and
unresolved provenance visible in the scoped seed receipt.
Do not infer qualification from a package name or version.

Pin this Ports revision, [sys.mk.in](sys.mk.in) and its SHA256 too.
The only template substitution is `@QUALIFIED_SH@`.
It must be the selected shell's absolute in-bundle invocation path.
For this fixed binding, reject whitespace and make metacharacters in that
path. Do not escape or reinterpret an unsupported path.

Retain every file, directory and symlink from the accepted upstream tree.
Keep its roster and hashes in the bundle inventory.
Move the original root `sys.mk` to `sys-upstream.mk` without changing bytes.
Create a new `sys.mk` from the exact template bytes.
All other upstream paths stay unchanged.
The template selects `.SHELL` before it includes an upstream makefile.
It also binds the ordinary `SHELL` make variable for recipes that use it.

```text
bundle-mk/
  sys.mk              exact instantiated Ports template
  sys-upstream.mk     unchanged original upstream sys.mk
  ...                 every other original upstream entry
```

The initial accepted upstream tree must not redefine `.SHELL` after the
entry point. Inventory makefile includes and active shell expressions.
Every consumed include must come from the plan's explicit accepted inputs.
A copied tree is not proof that every branch is safe to execute.

## Invocation

The bmake command prefix is:

```text
/absolute/selected/bmake -m /absolute/bundle-mk SHELL=/absolute/selected/sh
```

Add the recipe's `-C` argument after this prefix.
Do not add another `-m`, `MAKESYSPATH` or `MAKEFLAGS` value that changes it.
The command must bind an exact accepted `MAKECONF` before make reads package
metadata. An upstream `bsd.own.mk` can otherwise include a host configuration.
Bind selected compilers, archive tools and other required tools before the
first parse-time query. Upstream implicit rules retain their behavior;
their default tool names are not permission to search the host `PATH`.

The GNU make command prefix is:

```text
/absolute/selected/gmake SHELL=/absolute/selected/sh
```

Pass `SHELL` as a command-line variable for every initial and recursive GNU
make invocation. An environment-only assignment does not select its shell.
The producer must preserve the selected shell through configure-generated
makefiles and recursive make commands.

The [bmake manual](https://man.netbsd.org/make.1) defines `-m`, `.SHELL` and
command-line variables. The [GNU make manual](https://www.gnu.org/software/make/manual/html_node/Choosing-the-Shell.html)
defines GNU make shell selection.

## Acceptance

Accept the initial binary inputs only in the explicit bootstrap scope.
Do not make the first pilot depend on qualification of its future output.
Before the producer compiles anything, execute real package metadata with
the selected bmake, complete makefile tree and selected shell.
Check `.SHELL`, `SHELL`, `.SYSPATH`, recursive argv and every consumed file.
Exercise `!=` and `:sh` expressions through the selected shell.
Reject an absent shell, a missing upstream makefile, an include outside the
accepted inputs or a configuration fallback. Check that a failing shell
command still fails.

Then build the new make tools with the accepted GCC16 producer.
Ordinary native-toolset admission requires its own completed producer,
compiler/linker execution closure and runtime evidence.
The source entry and byte-preserving tree preparation alone do not prove
that a real package's metadata or native build passed.

## Initial Darwin utilities

[darwin-installed-utilities-v1.json](darwin-installed-utilities-v1.json) is a
fixed source-owned input and operation profile for a bounded initial SDK seed.
It names twenty installed executable members and one `gettext-lib` library.
The SDK owns original package admission, inventories, leases and execution.
The profile does not qualify installed binaries by package name or version.

Pin the exact profile and original/final prefixes in the accepted producer plan.
The initial output prefix is fixed. This profile does not promise relocation.
Preserve the original metadata and raw member hashes. Record transformed hashes
and actual operations separately. Existing installed-package byte equality
must not be used to admit modified outputs without an explicit derivation.

The selected official LLVM 23.1.3 `llvm-objcopy` provides its documented
`llvm-install-name-tool` invocation mode. It replaces the seventeen named
libintl dependencies and the library ID with the fixed final absolute path.
It removes RPATHs and regenerates existing ad hoc signatures.
No Apple tool discovery, compiler wrapper or system-tool fallback is allowed.
An absent original signature or unsupported input must fail.

Regular-file basenames stay unchanged. Aliases are explicit relative links.
The `awk` role selects `bin/nawk`; it does not silently create `bin/awk`.
A raw `awk` caller needs its own explicit route. The profile does not add grep.
Runtime paths, signatures, deterministic output and utility behavior still need
actual bounded checks. Ordinary source-built tools have a separate producer.

[darwin-installed-printf-v1.json](darwin-installed-printf-v1.json) is a separate
fixed subset for the `printf` role. It names only `coreutils-9.11` member
`bin/gprintf` and the same libintl library. It preserves the original GNU
invocation and selects the final relative `bin/printf` alias. Use the existing
SDK utility-relocation stage for two complete runs. Keep its original hashes,
actual derivation and derived package history separate from the first profile.
Compare the checked library with an already accepted library at the same final
prefix. Do not replace that library or expand an earlier result's member list.

[darwin-installed-build-utilities-v1.json](darwin-installed-build-utilities-v1.json)
is a separate fixed profile for initial package build and installation tools.
It selects these sixteen executable roles and the same libintl library:

- `coreutils-9.11`: `chgrp`, `chmod`, `chown`, `cp`, `install`, `ln`, `ls`,
  `mkdir`, `mv`, `rm`, `rmdir`, `touch`, and `sleep`.
- `pkg_install-20260227nb3`: `pkg_add` and `pkg_create`.
- `pkg_install-info-4.5nb3`: `install-info`.

Coreutils members retain their `g`-prefixed regular basenames and select
relative aliases. Package installers retain `sbin/pkg_add` and
`sbin/pkg_create`. The `install-info` role selects the real
`bin/pkg_install-info` member. It does not rename that executable or select an
unrelated `bin/install-info` file.

Use the same SDK stage for 34 operations: seventeen members in each of two
complete runs. Change libintl loads only for the thirteen coreutils members.
Keep each original package history separate, including its recorded compiler
and unresolved historical inputs. Require its own completed derivation.
Keep the earlier utility and printf profiles and results unchanged.
Compare libintl with an existing accepted library before provisioning new
members. This source profile does not prove utility behavior or admit a build.

## Initial BSD install

[bsdinstall.json](bsdinstall.json) uses the common `sysutils/bsdinstall` recipe.
The SDK compiles its two canonical C files with selected native GCC16.
It links the exact accepted `pkgtools/libnbcompat` static library and headers.
The input library must retain its actual producer, source and ABI evidence.
This initial program does not qualify an ordinary native toolset.

The ordered export applies `pkgsrc-bsdinstall-native-shell.patch` once.
The patch keeps the upstream implementation and its BSD notices.
It adds the opt-in `EMBERBSD_BSDINSTALL_SHELL` compile-time definition.
The ordinary default remains `_PATH_BSHELL`.
Both `-S` and `-a` use the selected shell in the initial build.
The existing `TARGET_STRIP` definition selects the native strip executable.
Require one absolute selected invocation for both roles.
Do not pass an argv tail through either C string definition.

The SDK owns leases, source admission, exact driver and ABI arguments, execution
and separate stdout/stderr checks.
Owner Git evidence covers this profile, its patch and `pkgsrc/export.conf`.
The composed pkgsrc C files are derived source bytes.
They are not literal members of the Ports commit.
Bind the pinned pkgsrc Git archive and the ordered zero-fuzz patch to the full
prepared source inventory before execution.

The fixed cases use umask `022` and check file bytes, modes and errors.
They check `-U`, regular and symbolic modes, directories, same-file refusal,
missing sources, selected strip execution and both after-install outcomes.
Canonical `-U -d` keeps the mode from `mkdir` and the umask.
It does not apply the requested directory mode.
The two-source recipe does not enable `SUPPORT_MTREE`.
The metalog case must reject `-M`; it must not claim a successful metadata log.
Do not remove `-U` or filter installer flags to accept GNU install instead.
Actual GCC16 and semantic execution remain required acceptance steps.

## BSD installer in the completed native bundle

The scoped Darwin profile adds the common `sysutils/bsdinstall` package to the
GCC16 bootstrap closure. It adds the edge only at the GCC root. Infrastructure
recipes do not gain a dependency on the installer they must first build.
The installer package depends on common `shells/mksh` and `lang/llvm`. Its child
shell and strip paths use their final `LOCALBASE/bin` outputs. They do not retain
initial seed paths. The build still uses accepted initial compiler and tools.

`MAKECONF` is read before `PKGPATH` exists and again during package preferences.
The package policy waits for `PKGPATH` outside the early one-time guard. The
installer recipe reads its optional shell definition after those preferences.
Ordinary callers retain the upstream defaults.

The initial direct producer remains initial-only. It does not qualify a native
toolset. A completed bundle must select `bin/bsdinstall` for the `install` role,
retain the actual package build and graduation evidence, and pass the BSD
installer semantic cases. GNU `ginstall` can remain a distinct utility. It cannot
satisfy the BSD `-U` installation contract. The NativeToolset mapping pins the
selected `install` path; it does not infer installer semantics from a role name.

## First ordinary foundation

The Darwin bootstrap profile adds the common make, utility, package-tool and
Meson providers only at the `lang/gcc16` root. Standard dependency edges supply
`bootstrap-mk-files` for bmake and Ninja for Meson. Named metadata observations
must establish the complete acyclic production graph before execution.
Do not infer a fixed graph size from the root list.

The accepted initial shell is mksh. The existing bmake, gmake and Ninja recipes
select the final `${PREFIX}/bin/mksh` for their installed default shell.
Bmake also selects `${PREFIX}/share/mk`. Keep the initial build shell separate
from these final paths. Verify the actual configure arguments and output routes.
Run `profiles/development-toolchain/tests/darwin-bootstrap-foundation.py` for
finite source controls. These controls do not execute make or qualify outputs.

Only completed providers in the accepted full plan can use its graduation.
Keep initial tools in their original scope. Select `bin/bsdinstall` for ordinary
`install`, even when coreutils also installs `bin/ginstall`. The remaining OS
hostname program can be rebuilt with qualified GCC after foundation admission.
It does not require another GCC bootstrap.

## Initial package tools

[pkg-install.json](pkg-install.json) follows `bootstrap/bootstrap` from the
pinned pkgsrc source. It builds the current common libarchive as a static
library without compression backends or archive CLI programs. It then uses
the supported `pkg_install --enable-bootstrap` mode and the accepted
`pkgtools/libnbcompat` headers and static library. Build the four `pkg_add`,
`pkg_admin`, `pkg_create` and `pkg_info` programs with selected native GCC16
and BSD make. Do not run the general bootstrap shell script.

This is an initial-only producer. Bootstrap mode excludes package deletion,
signature objects and libfetch. It does not remove required-library checks.
The full common package recipe retains its ordinary dependencies and features.
The Darwin initial profile selects `PKG_COMPRESSION=none`, as the canonical
bootstrap does for early binary packages. Package creation passes `-F none`.
It does not infer a filter from the `.tgz` filename or call an ambient compressor.
The ordinary configuration retains its existing compression default.

Bind the complete canonical source trees, the bootstrap script, the ordered
`pkgsrc-pkg-install-dyld-cache.patch` and the source owner evidence before
execution. Only literal owner files have Ports Git membership. Composed C
sources have their separate canonical export and content derivation. Keep
source file modes and mtimes in that proof. No release bytes become Git members
by copying them. The input libnbcompat component retains its producer, source
and ABI evidence. It does not imply a successful full SDK build.

The SDK owns exact compiler and ABI arguments, selected tools, work-only
paths, global link serialization, process drainage and admission. The fixed
case tokens `@WORK@` and `@HOST_KERNEL_VERSION@` mean the accepted work root
and actual Darwin kernel version. They are not caller-supplied shell text.
All generated package databases, source payloads, archives and install roots
stay under that work root. No case executes an installed historical pkgtool.

The semantic cases check the four versions, package matching, uncompressed
creation, a real installation and registration, and the installed payload
checksum. They require the active Darwin cache to satisfy the declared
`/usr/lib/libSystem.B.dylib` dependency. A missing library must fail. A separate
`-P` target root must not use the host cache. No force, fake-install, platform
override, script fixture or ignored error is permitted. Source controls alone
do not establish compiler, package or runtime acceptance.

For finite C diagnostics, run the explicit SDK control Python on
`scripts/tests/prepare_cache_fixture.py --source <export>/pkgtools/pkg_install/files/add/perform.c --output <fresh-work>/pkg-install-check-requires.inc`.
The helper extracts the patched functions. It does not start a build.
Compile `scripts/tests/pkg_install_cache_fixture.c` with the selected GCC16
driver and ABI tuple, `-I<fresh-work> -std=gnu99 -Wall -Wextra -Werror`, and
`-DTEST_DYLD_CACHE=0`, then `-DTEST_DYLD_CACHE=1`. The fixture checks both
source branches. It does not replace the real package runtime cases above.
