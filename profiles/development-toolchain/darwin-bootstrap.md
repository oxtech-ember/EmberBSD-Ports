# Prepare native Darwin GCC16 package metadata

This policy is for a scoped SDK bootstrap producer on Darwin AArch64.
It is a source candidate until real package metadata and native builds pass.
It does not qualify any input binary or ordinary output toolset.
The SDK owns input admission, host facts, inventories and child execution.
Ports owns the shared recipes and the pkgsrc command mapping.

## Source export

Use the repository's canonical export interface:

```text
# Provide a verified source-data export at /absolute/new-pkgsrc. See the root README.
```

Initialize `upstream/pkgsrc` at the repository's recorded gitlink first.
The export checks that revision. It applies `pkgsrc/export.conf` in order.
Do not copy a second GCC recipe into the SDK.
The Python callable uses explicit Git and patch commands.
The exact SDK source-export controller is not implemented.
Use the root [source-data composition procedure](../../README.md#package-integration)
for source editing. That operation does not admit its host tools into SDK builds.

The export installs [darwin-bootstrap.mk.conf](darwin-bootstrap.mk.conf) as
`EMBERBSD-DARWIN-BOOTSTRAP-MK.CONF` beside the other exported profiles.
The [infrastructure patch](patches/pkgsrc-darwin-bootstrap-policy.patch)
loads an explicit MAKECONF before pkgsrc can detect its host or default PATH.
The normal Darwin branches stay unchanged when this policy is not selected.

## Accepted inputs

Select `EMBERBSD_DARWIN_BOOTSTRAP=yes` in the initial bmake command.
Use the SDK's complete [make binding](../common-build-tools/bootstrap/README.md).
It binds the selected make, complete system-makefile tree, shell and MAKECONF.
The producer must reject inherited make flags, compiler caches and command-line
assignments that can replace this plan's inputs.

The exact pinned MAKECONF contains SDK-generated input assignments. It then
includes `/absolute/export/EMBERBSD-DARWIN-BOOTSTRAP-MK.CONF`.
Keep that include and all consumed configuration files in the accepted inventory.
This is a make-variable adapter for the SDK's existing accepted selection.
It is not a second descriptor, receipt or qualification format.

| Make input | SDK source |
| --- | --- |
| `EMBERBSD_DARWIN_HOST_OS` | Actual host OS, `Darwin` |
| `EMBERBSD_DARWIN_HOST_CPU` | Actual CPU in pkgsrc form, `aarch64` |
| `EMBERBSD_DARWIN_HOST_KERNEL_VERSION` | Actual kernel release |
| `EMBERBSD_DARWIN_HOST_PRODUCT_VERSION` | Actual macOS product version |
| `EMBERBSD_DARWIN_HOST_PKGSRC_OPSYS_VERSION` | Product version encoded as major/minor/patch, two digits per field |
| `EMBERBSD_DARWIN_MAKE`, `EMBERBSD_DARWIN_GMAKE` | Shell-quoted complete SDK `command('make')` and `command('gmake')` tuples |
| `EMBERBSD_DARWIN_SH` | Selected `command('sh')[0]` |
| `EMBERBSD_GCC16_SEED_CC`, `EMBERBSD_GCC16_SEED_CXX`, `EMBERBSD_GCC16_SEED_CPP` | Shell-quoted selected driver tuple plus the separately accepted language/ABI arguments |
| `EMBERBSD_GCC16_LLVM_MC`, `EMBERBSD_GCC16_LD64_LLD`, `EMBERBSD_GCC16_DSYMUTIL` | Selected assembler, Mach-O linker and debug tool paths |
| `EMBERBSD_GCC16_AR`, `EMBERBSD_GCC16_RANLIB`, `EMBERBSD_GCC16_NM`, `EMBERBSD_GCC16_STRIP` | Selected archive and symbol tool paths |
| `OSX_SDK_PATH`, `EMBERBSD_GCC16_DARWIN_SDK_VERSION` | Accepted native ABI root and its metadata version |
| `MACOSX_DEPLOYMENT_TARGET` | Deployment from the accepted fixed GCC binding |
| `EMBERBSD_DARWIN_JOBS`, `EMBERBSD_DARWIN_CPU_BUDGET` | Positive decimal jobs and the accepted coordinator budget; jobs must not exceed the budget |
| `EMBERBSD_GCC16_LINKER_LAUNCHER` | SDK control-plane link launcher command; required for parallel GCC bootstrap |
| `WRKOBJDIR`, `DISTDIR`, `PACKAGES`, `LOCALBASE`, `PKG_DBDIR` | Explicit shared work/cache roots and the isolated producer output/package database |
| `EMBERBSD_DARWIN_UTILITY_BIN` | Inventoried directory with only accepted utility invocation paths |
| `EMBERBSD_DARWIN_NATIVE_TOOLS` | Exact names of accepted native utility roles |
| `EMBERBSD_DARWIN_TOOL.name` | Absolute selected path for each native utility name |
| `EMBERBSD_DARWIN_SOURCE_TOOLS` | Explicit utility names to build from their shared Ports recipes |
| `NATIVE_PKG_ADMIN_CMD`, `NATIVE_PKG_INFO_CMD` | Accepted package metadata tool paths |

The SDK must verify host facts against the current machine and verify the
pkgsrc numeric encoding. Do not substitute an SDK version for a host version.
A compiler target tuple does not establish the running host's identity.
All paths in this bounded interface must exclude whitespace and make syntax.
The SDK must verify every command word, inventory member and path boundary.
The make policy only checks the structure needed to refuse an absent input.

The SDK bounds the CPU budget against the current host before execution.
Its saved plan retains that accepted budget. The make policy does not query
the host or invent a processor count. See the
[native GCC link route](gcc-darwin-host.md#shared-link-resource) for the
launcher scope. The SDK constructs this command from its own pinned Python
control plane, SDK script and resource paths. This Python service is not a
native compiler or generator provider.

The GCC compiler command keeps the fixed `-B`, pinned `-specs` and deployment
arguments in their accepted order. See [the GCC binding](gcc-darwin-host.md).
Use `ld64.lld` as the linker invocation. A nominal `ld` driver query is not a
Mach-O linker command. Keep native ABI flags separate in the SDK selection.
Emit them once in each compiler command. Emit accepted link-only flags in
`LDFLAGS`. Do not append the same ABI flags through another make variable.

## Compiler and utility routes

Pkgsrc's compiler selection uses `CC:[1]` for executable discovery.
Its later compiler-path stripping keeps the remaining arguments.
The stock cwrappers configuration has a single executable `exec=` field.
It does not split that field as a shell command.

In this opt-in mode, `gcc.mk` puts the selected executable in `CC`, `CXX`,
`CPP` and each `PKG_*` wrappee. It transfers the accepted command tail once
through `CWRAPPERS_PREPEND.*` and the existing legacy `_WRAP_EXTRA_ARGS.*`.
The standard wrappers still apply package transformations and diagnostics.
The GCC recipe's own configure input uses the complete accepted seed command.
Its stage 1 does not depend on another wrapper adding that command a second time.
No source specs file or ad hoc executable wrapper is generated by this policy.

The selected utility PATH must provide the native invocation names used by
parse-time shell expressions. Defining only `TOOLS_PLATFORM.name` does not
bind a raw `env`, `awk` or other bare command in an upstream expression.
The policy requires an explicit initial utility roster and package tools.
The Darwin native-tool map does not run xcrun to discover m4 or yacc.
A requested tool needs an accepted native path or an explicit shared source
provider. An unknown tool produces a parse error. Source-provider selection
adds the normal recipe dependency; it does not supply a runnable input yet.
The selected shell supplies only the named standard builtins in that map.
`printf` is not one of them: some POSIX shells, such as mksh, have no
`printf` builtin, and a bare name makes the pkgsrc tool wrapper run itself
until the process limit is reached. Select `printf` as a native path.
The map keeps the standard pkgsrc arguments for `gunzip`, `gzip` and `mkdir`;
without `mkdir -p` the first work directory cannot be created.
Configure scripts and Makefiles also run bare `ar`, `nm`, `ranlib` and
`strip`. The policy creates the first three in the pkgsrc tools directory
from the selected `EMBERBSD_GCC16_*` commands and selects
`TOOLS_PLATFORM.strip`, so `mk/tools/strip.mk` keeps its no-op for
unstripped installs. The utility PATH does not supply them.
A tool without standard arguments maps to its exact path, with no trailing
space: pkgsrc scripts run some of them quoted, such as `"${AWK}"`.
The `[`, `echo`, `false`, `test` and `true` maps invoke that shell
explicitly with the exported helper `mk/tools/emberbsd-darwin-builtin.sh` and
the builtin name. The helper forwards the original arguments through `"$@"`.
This preserves the selected shell's options, escapes and statuses.
The command has no quoted words: pkgsrc passes tools such as `TEST` to
scripts like `mk/extract/extract` in the environment, and they run `${TEST}`
unquoted. A quoted `-c` command would split into broken words there.
pkgsrc also reduces `TOOLS_ECHO`, `TOOLS_TEST`, `TOOLS_TRUE` and
`TOOLS_FALSE` to the first word of the map, the shell alone. The policy sets
them to the full command, and `tests/darwin-bootstrap-builtin-env.py` runs
each value the way these scripts do.
Compatibility-mode bmake can otherwise bypass the shell for a simple recipe
and try to execute an absent external builtin name.
The finite [echo fixture](tests/darwin-bootstrap-echo.mk) compares this route
with the same builtin forced through the selected shell. It covers empty,
nonempty, option-leading and backslash values, plus recursive `show-var`.
Its [capture oracles](tests/darwin-bootstrap-source.py) also check the direct
named `-V` expression values. They execute no tool or captured output.
`ld64.lld -v` reports "compatible with GNU linkers". libtool's linker probe
therefore classifies it as GNU ld, and configure scripts such as libffi's
add ELF-only options like `--version-script`. The policy supplies
`lt_cv_prog_gnu_ld=no` and `lt_cv_prog_gnu_ldcxx=no` in `CONFIGURE_ENV`.
`tests/darwin-bootstrap-libtool-linker.py` checks this with an accepted MAKECONF.

Some Darwin build systems run Apple `ranlib -c`; OpenSSL's `darwin-common`
target does. `llvm-ranlib` rejects `-c` and already puts common symbols in
the archive index, so the policy passes the selected ranlib as `RANLIB` in
`CONFIGURE_ENV`. `tests/darwin-bootstrap-ranlib.py` checks the evaluated value
for `security/openssl` and runs it on an archive with a common symbol.
Packages such as `archivers/zstd` request GNU grep as `ggrep`. As on
ordinary Darwin, the policy gives `ggrep` the selected `grep` unless the plan
selects a native `ggrep`. Ports grep needs bash, bison, flex and help2man,
and help2man reaches zstd again through gettext-tools and python.
`tests/darwin-bootstrap-ggrep.py` checks both cases for `archivers/zstd`.
ELF inspection tools such as `readelf` have no Darwin base provider. Select
them as native utilities from the accepted seed LLVM tools.

The initial conservative parse-time roster is `awk basename cat cut date
dirname env expr grep head id pwd sed sort tail tr uname uniq wc`.
`pkg_info -V` and `pkg_admin pmatch` also need actual accepted providers.
The GCC recipe and its recursive dependencies can require more utilities,
including GNU make, Perl, makeinfo and pkg-config. Their exact evaluated DAG
and active utility queries remain a real metadata acceptance step.
Do not invent successful cached versions or use a failed query's fallback
value as qualification evidence.

## Verification limits and next gate

The source controls check the early guard, native-tool branch, compiler tail
placement and preservation of ordinary source branches. They execute no make,
compiler, linker or selected input binary. They do not evaluate a pkgsrc DAG.

The next gate runs the SDK's fixed variable and dependency queries for `lang/gcc16`.
Use the accepted command, complete make tree and this exact profile. Capture all
children, consumed includes, package database reads and resulting dependencies.
Check that stale host-detection values do not change the accepted facts.
Check refusals for an absent fact, utility, MAKECONF, source provider and jobs
outside the accepted budget, and parallel jobs without the link launcher.
Check that no child uses the original installed prefix,
CLT discovery, an unselected system utility or an uncontrolled PATH.
Then replay the wrapper routes and the GCC stage-1 configure command.
A source-only pass cannot replace these gates or the full GCC bootstrap.
