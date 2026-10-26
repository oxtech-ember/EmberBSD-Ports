# GNU diffutils and findutils

The common recipes select GNU diffutils 3.12 and findutils 4.11.0.
The GNU release archives are the source owners. The recipes keep their GNU
GPLv3-or-later notices and the inherited NetBSD pkgsrc integration.
The recipe updates and finite bootstrap specifications are AI-assisted EmberBSD
work. They are not submitted upstream.

## Ordinary packages

`pkgsrc/devel/diffutils` keeps the default `nls` option and its gettext provider.
It builds all four programs and installs the existing `g` names and GNU aliases.
The inherited shell/mkdir and installed-diff-path patches have refreshed exact
release context. `pkgsrc/sysutils/findutils` retains gettext, find, locate,
updatedb, xargs, their documentation, and the `/var/db/locate.database` path.
The PLIST locale rows follow each release's `po/LINGUAS`.

The old findutils Solaris forward-declaration patch is removed. Its complete
removed declaration is absent from the 4.11.0 `gnulib-tests/localename.c` source.
No test is disabled. The locate database patch retains its original behavior.
FreeBSD and DragonFly carry an updatedb `su` command adaptation. OpenBSD carries
a platform-specific `fseeko` adaptation. These are not Darwin C changes.
MacPorts supplies these current release versions without a modern Darwin C patch.

The diffutils configure patch uses `cmp -s` in its six file-equality checks.
Each old test consumed only the zero/nonzero result, with no diff output.
The patch preserves its branches and redirections. It retains all grep and sed
capability tests. It supplies no cached compiler or utility result.
Both configure patches first test whether optional `xargs` is available.
A missing tool takes the upstream no branch. A present tool runs the complete
original capability test. A failed or missing program is not a successful probe.

Both recipes stage the [common diagnostic helper](files/emberbsd-configure-diagnostics.sh)
from the export. They do not maintain separate helper implementations.
When `EMBERBSD_GCC16_UNAME` selects the SDK uname, the recipes pass
`EMBERBSD_CONFIGURE_SDK=yes` and the exact `EMBERBSD_CONFIGURE_UNAME` path.
The configure and configure.ac hooks route absolute legacy diagnostic commands
through that helper. Supported uname queries use the selected program.
Optional legacy probes report unavailable. They never execute system paths.
Unset SDK mode preserves upstream diagnostics and all ordinary feature tests.
The paired source patch retains release generator outputs. Before configure,
the recipes align configure.ac to the unchanged aclocal.m4 release timestamp.
This prevents a spurious Autoconf regeneration dependency during bootstrap.

## Finite initial source builds

[Diffutils](bootstrap/gnu-diffutils.json) and
[findutils](bootstrap/gnu-findutils.json) use the existing
`emberbsd-native-bootstrap-program` version 1 envelope.
They name their canonical recipe. They do not repeat an archive URL, checksum,
or patch recipe. The prepared source must include that recipe's complete patches.
Use these source-owned target and behavior definitions with the selected SDK tools.

The only initial feature argument is the upstream `--disable-nls` option.
It limits this initial provider to the selected programs. It does not change the
ordinary recipes' translation policy. No warning, test, or compiler diagnostic
is disabled. Do not use this subset as an ordinary package result.

Build a checked source-native `cmp` and `hostname` first. Build the initial GNU
`diff` next. Build `find` and `xargs` after it. The selected PATH and role bindings
must exclude failed or unavailable providers. Every listed utility must come from
the selected SDK. Do not add a system PATH fallback.

Source preparation also stages the exported common diagnostic helper at the
release root, as the ordinary recipe does. Initial configure sets
`EMBERBSD_CONFIGURE_SDK=yes` and `EMBERBSD_CONFIGURE_UNAME` to the selected uname.

The SDK must use the exact selected GCC16 command tuples and native ABI flags.
Use the selected GNU make tuple, including its CLI `SHELL` binding, for every
listed target. Keep build and host triplets explicit. Preserve release mtimes
so these targets do not regenerate Autoconf or Automake source files.
The consumer owns fresh source/build/output paths, resource controls, process
logs, deadlines, read leases, heavy-link serialization, and full child drainage.

The diffutils sequence builds generated library headers, version/path headers,
and only `src/diff`. The inherited installed-diff-path substitution is relevant
to ordinary diff3/sdiff, which this initial specification does not build.
The findutils sequence builds generated gnulib headers, `libfind.a`, `find`, and
`xargs`. It does not use a nonexistent `--disable-locate` configure option.
It does not call the recursive top-level all, install, clean, or uninstall target.
The inspected `am__xargs_n` uses in findutils are uninstall helpers.

The runtime cases define exact initial semantic and error results in `LC_ALL=C`.
A case with `command_role: "sh"` appends the exact selected shell command tuple
and its fixed `command_args`. Only this literal role is defined. The SDK must pin
and recognize these exact cases; this is not an arbitrary role or argv interface.
In particular, xargs never uses its implicit `/bin/echo` command in these cases.
Find's explicit child case also uses the selected shell.

Source checks establish archive/patch identity and finite source transformations.
Actual configure, native program builds, runtime cases, loaded-library checks,
upstream suites, ordinary package installation and cross-package acceptance are
separate work. No compiled or installed utility acceptance is claimed here.

## Source checks

Use the two verified release archives and explicit SDK patch, shell and uname paths.
Use a new absolute work directory. The check does not run configure or make.

```sh
/absolute/python -B profiles/common-build-tools/tests/gnu-utilities.py \
  --diffutils-archive /absolute/distfiles/diffutils-3.12.tar.xz \
  --findutils-archive /absolute/distfiles/findutils-4.11.0.tar.xz \
  --patch /absolute/sdk/bin/nbpatch \
  --shell /absolute/sdk/bin/mksh --uname /absolute/sdk/bin/uname \
  --work /absolute/new-source-check
```

The check verifies all recipe archive hashes, exact zero-fuzz patch application,
reverse identity, six equality replacements, two optional-tool guards, complete
locale rows, and ordinary NLS policy. A changed-source control must fail.
It runs only the diagnostic hook with the selected SDK shell and uname.
Missing, relative and system uname selectors must fail before a diagnostic runs.
All eight unsupported legacy commands must report unavailable without executing.
The check also preserves the original unset-mode invocation.
It retains its finite source work and result for the caller to inspect.

## Source provenance

- [GNU diffutils 3.12 release](https://ftp.gnu.org/gnu/diffutils/diffutils-3.12.tar.xz)
- [GNU findutils 4.11.0 release](https://ftp.gnu.org/gnu/findutils/findutils-4.11.0.tar.xz)
- [FreeBSD diffutils checksums](https://github.com/freebsd/freebsd-ports/blob/main/textproc/diffutils/distinfo)
- [FreeBSD findutils checksums](https://github.com/freebsd/freebsd-ports/blob/main/misc/findutils/distinfo)
- [MacPorts diffutils recipe](https://github.com/macports/macports-ports/blob/master/sysutils/diffutils/Portfile)
- [MacPorts findutils recipe](https://github.com/macports/macports-ports/blob/master/sysutils/findutils/Portfile)
- [NetBSD diffutils integration](https://github.com/NetBSD/pkgsrc/tree/fff4deb639a1a640476203c80f752fb77b6cb14b/devel/diffutils)
- [NetBSD findutils integration](https://github.com/NetBSD/pkgsrc/tree/fff4deb639a1a640476203c80f752fb77b6cb14b/sysutils/findutils)

Each canonical distinfo records the archive Size, SHA256, SHA512 and BLAKE2s.
The expected SHA256 and size match the independent FreeBSD and MacPorts pins.
Patch SHA1 follows pkgsrc: remove complete LF records that contain `$NetBSD`.
Each recipe patch has its current checksum in distinfo.
The additional archive hashes are computed from those verified release bytes.
The recipes keep their inherited NetBSD patch origin. Upstream licenses remain
in the source archives. Do not substitute an older recipe because it is in pkgsrc.
