# ELF Tool Chain source for base libelf

This recipe owns the ELF Tool Chain source and the BSD libelf/common patch set.
The OS owns native build rules, installed paths and SONAME `libelf.so.2`.
The SDK owns production source preparation and its receipts.

Upstream lists 0.7.1, released on 2016-02-18 at SVN r3417, as its newest release:
<https://sourceforge.net/p/elftoolchain/wiki/Releases/>.
Use the original `elftoolchain-0.7.1.tar.bz2` archive from the literal recipe URL.
Its size is 5361427 bytes. Its SHA256 is
`44f14591fcf21294387215dd7562f3fb4bec2f42f476cf32420a6bbabb2bd2b5`.
`distinfo` also verifies its SHA512 and BLAKE2s hashes.

## Source ownership

`patch-00-bsd-libelf-common` carries the complete libelf/common delta from
[the published OS source](https://github.com/oxtech-ember/EmberBSD/tree/c5d396f5698b68e956b29ee5b256bc7877e6c517/external/bsd/elftoolchain/dist).
It preserves the original licenses, authors, upstream SVN identifiers and
NetBSD CVS identifiers. Patch assembly and checks are AI-assisted EmberBSD work.
It does not include the native makefiles outside the OS `dist/` directory.
The other original pkgsrc patches remain in the same ordered patch set.

`patch-02-symbol-table-indices` backports only the NetBSD r4309 definition of
`STN_UNDEF` and its generated-header invocation. The source is the upstream
sync in [NetBSD commit c441046e](https://github.com/NetBSD/src/commit/c441046e2806d3fa9be50528c9ca08f6a871582d).
The generated ELF definitions header must expose this symbol-table index to
libelf consumers. No other r4309 changes are included.

`files/base-source.json` records the upstream archive, public OS pin, exact
`common` and `libelf` Git tree IDs, and every file in that BSD snapshot.
Its `files` map contains 128 relative paths. Each entry has a byte size, mode
and SHA256. Source files use the Git regular-file mode 0644.
`packaging_overrides` replaces four expected entries in the prepared source:

- `libelf/Makefile` uses major 2 and minor 0.
- `libelf/Version.map` exports the existing BSD `elf_getversion` function.
- `common/sys/elfconstants.m4` defines `STN_UNDEF` as symbol index zero.
- `common/sys/elfdefinitions.m4` emits that definition in the generated header.

Each override binds its original `base_sha256` and its final size, mode and
SHA256. Merge these overrides over `files` to check the complete prepared
subset. No extra file or link is allowed under `common/` or `libelf/`.
The two M4 overrides are the only code-generation source differences from the
OS snapshot. The other 70 C, header and M4 files remain byte-identical.
The prepared upstream root is still `elftoolchain-0.7.1`.
It contains sibling `common/` and `libelf/` directories.

Production source preparation must verify the clean Ports pin, pristine
archive and every recipe patch. It must apply the complete patch set without
configure commands or source substitutions. It must validate this manifest
before publishing a new immutable root. The SDK adds its own source receipt
and an exact copy of recipe `distinfo` as `ports.distinfo`.
An OS build can install that identity as
`/usr/share/emberbsd/ports/elftoolchain.distinfo` after source validation.
This receiver does not create an installed-base acceptance marker.

## Provider and portability boundaries

The complete portable package is refused on marked EmberBSD targets, in an
EmberBSD export, or when the selected target root contains the base marker.
The marker lookup uses `TOOLS_CROSS_DESTDIR`. A host marker cannot qualify a
cross target. This follows the existing base-libedit provider policy.
Mesa builtin selection and OS integration remain separate changes.

Other systems retain the portable full-package build. The BSD `Elf_Data`
layout changes alignment and size fields from `size_t` to `uint64_t`.
That changes the 32-bit layout, so the portable library uses ABI 2.
Its PLIST names `libelf.so.2` and `libelf.so.2.0`.
The new generated `include/sys/elfdefinitions.h` and its wrapper at
`include/elfdefinitions.h` are installed separately despite the global
pkgsrc `INCSDIR` override. The recipe obtains the generated file from the
actual BSD make object directory with the same `MAKE_ENV` and `MAKE_FLAGS`.
The GCC floor is 16.2. Compiler diagnostics remain enabled.
The original platform limits for the full portable package remain in place.

## Source regression

Run the finite check with Python 3.15 and explicit tool paths:

```sh
python3.15 -B -I -S tests/source.py \
  --archive /absolute/distfiles/elftoolchain-0.7.1.tar.bz2 \
  --os-source /absolute/EmberBSD \
  --os-revision c5d396f5698b68e956b29ee5b256bc7877e6c517 \
  --git /absolute/git --patch-tool /absolute/nbpatch \
  --bmake /absolute/bmake --m4 /absolute/m4 \
  --work /absolute/new-source-check
```

The OS revision must be an exact commit with the two recorded Git trees.
Fetch any missing Git objects explicitly before this check. The check refuses
implicit network access and does not change the checkout or refs.
It verifies the full OS subset independently from Git archive bytes.
It checks the original archive, every pkgsrc patch checksum, real patch
application, and all prepared subset bytes and paths.
It rejects unpatched source, an altered header and an obsolete extra file.
It runs M4 on the prepared source and checks that the generated header defines
`STN_UNDEF` exactly once. A source copy without `patch-02-symbol-table-indices`
is the causal control and must not define the symbol.

The check uses NetBSD patch options `-f -E -p0 -F0 -V none` and a separate
`-B` backup directory for each patch. These scratch backups stay outside the
prepared root. Any source backup or reject file fails the check.
The check also runs the actual recipe through BSD make metadata fixtures.
It covers native and cross provider guards, a wrong-host-root causal control,
the compiler floor and the portable ABI file list.
A data-only fixture executes the production header-install target with the
real BSD make object query. It checks quoted flags, environment routing and
refusal when that query fails.

`result.json` and command logs remain in the requested work directory.
Extracted sources and metadata fixtures are removed after the check.
This check generates a header but does not compile C, invoke configure, build
or install a real package, run target programs, or qualify a complete SDK toolset.
The full portable package build, installed ABI/runtime consumers and the
new OS source integration require their own acceptance.
