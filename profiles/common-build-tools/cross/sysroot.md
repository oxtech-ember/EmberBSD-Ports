# EmberBSD sysroot provenance

The target system is EmberBSD. Its retained NetBSD ABI, compiler triplets,
ELF notes and pkgsrc platform variables are compatibility interfaces. They
do not select upstream NetBSD kernel, libc, headers or drivers as substitutes
for the fork. Preserve upstream copyright and source identifiers.

## Preparing and updating a sysroot

Use a destination tree built from a pinned EmberBSD commit and configuration.
Keep its base-library, header, startup-object and toolchain provenance together:
source revision, compiler and build configuration, artifact hashes, and the
target acceptance performed. Target pkgsrc metadata covers packages under
`/usr/pkg`; it does not establish the origin of base `/lib`, `/usr/lib` or
`/usr/include`.

Do not complete a partially populated sysroot by extracting whichever files
are missing from upstream `base` or `comp` sets. Different paths can resolve
to distinct libc copies. A complete fork build is the preferred replacement;
a component-only repair must identify every replaced alias, preserve rollback
outside the sysroot, and state which other components remain unverified.
Old recovery libraries must not remain reachable through compiler or loader
search paths. A profiled libc archive cannot be replaced with an unprofiled one.

The common cross profile compares `/lib/libc.so`, `/lib/libc.so.12`,
`/usr/lib/libc.so` and `/usr/lib/libc.so.12` before extraction. Missing or
different bytes stop that package build. This consistency check cannot tell
whether four identical copies are from EmberBSD; the source receipt and
regression tests remain necessary. Reassess already-built consumers after
changing any selected provider. A successful package build does not certify
an entire base release.

## Pinned AArch64 base and comp imports

The SDK owns [OS release orchestration and receipt validation](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/os-release.md).
The OS owns distribution rules, set contents and target execution probes.
Its complete snapshot at `6dd57144183678938164b4c2dcfc370cdbde8473`
passes GCC16 C11/C++20, shared/static libc CAS and GNU M4 checks in AArch64
QEMU. The owning guide records hashes and scope. Binary publication remains
pending; a retained CI candidate does not establish a public download channel.

Select a published `build-FULL_SOURCE_COMMIT-aarch64-sysroot` release from
`oxtech-ember/EmberBSD`. Record its full source commit and the SHA256 of its
`manifest.json` through a trusted channel. A checksum downloaded beside a
modified manifest does not establish that trust.

Use host Python, the selected SDK source, curl, and xz.
Run the importer with a new absolute work directory:

```sh
export EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK
python3 -B profiles/common-build-tools/cross/fetch-sysroot.py \
    FULL_SOURCE_COMMIT TRUSTED_MANIFEST_SHA256 /absolute/new-sdk-work
```

The importer verifies the manifest pin, repository, architecture, source
identity, set hashes, build profile, and required target qualification.
It accepts historical `emberbsd.aarch64.sysroot.v1` and modern v2 and v3.
Version 1 keeps its original checks. Version 2 selects GCC build profiles 2/3;
version 3 selects Clang build profiles 4/5. Both modern versions use the
selected SDK build and qualification validators, including compiler and runtime
identity, source and output bindings, target execution and evidence hashes.
The v2 target corpus additionally identifies its test sources and verifies
ordinary libm and setjmp checks. An older SDK lacking these validators cannot
import a newer profile.

It extracts `base.tar.xz` and `comp.tar.xz` into `new-sdk-work/sysroot`.
It records the selected inputs in `receipt.json` and file identities in
`sysroot-files.json`. The destination must not exist before the command.

Extraction preserves regular-file bytes and modes. Absolute target symlinks
become relative links within this snapshot. Separate base and comp sets can
share a symlink only when its target and mode match exactly. Traversal,
escaping links, conflicting members, repeated non-directory members within
one archive, unsupported entry types, corrupt xz, and data after the tar end
marker fail the import. This is an isolated compiler
sysroot. Do not extract these sets over the host or a running target.

NetBSD `maketars` writes the sets with `pax --gnu`. A name or link target
of 100 bytes or more then has a GNU `L` or `K` record named
`././@LongLink`. The header field keeps only the start of the value.
The importer applies the record to the next member and checks the complete
value like a normal name or target. The Clang comp set of OS `2e5ec0754fdc`
has such a link for a libc++ `__cxx03` header. A record must hold one UTF-8
value of at most 1024 bytes (`MAXPATHLEN`), and the value must start with the
header field. A long link record must precede a link. A long name record
cannot precede an old-style type 0 member. Repeated or unused records and pax
extended headers fail the import.

The OS sets supply headers, startup objects, link libraries, and runtime
providers from one fork build. The selected host cross compiler and application
runtime remain separate inputs. This importer does not create an SDK application
sysroot build or transfer record. Clang profile 5 includes base C++ runtime;
profile 4 requires its selected runtime separately. They do not supply a Linux cross compiler or
the Ports GCC16 package. For the GCC16 override, add its target headers and
runtime through the [cross compiler profile](../../development-toolchain/cross/README.md)
and record their separate provenance. Keep the original OS snapshot intact.
Historical schema-1 sets use the in-tree GCC12 bootstrap; their GCC16 consumer
checks do not mean the base was compiled with GCC16. Schema-2 sets use the
common GCC16 producer with a staged runtime as a build input. Runtime and
headers from the GCC16 package remain separate Ports inputs for both formats.
Keep the versioned provenance; do not describe both formats as the same build.

Run the archive extractor regression on the Linux host:

```sh
python3 -B profiles/common-build-tools/cross/tests/sysroot-archive.py
python3 -B profiles/common-build-tools/cross/tests/fetch-sysroot.py
```

The regressions cover archive mechanics, hostile inputs, and CLI refusal
controls with a local download fixture. They do not establish HTTPS behavior
or target execution. Actual set and target acceptance belongs to the selected
release's bound qualification.

## Verified libc repair, 2026-10-09

A graphics cross sysroot contained the accepted fork's shared libc in
`/usr/lib`, an old upstream copy in `/lib`, and an old static archive.
The cause was a local helper that filled missing paths from upstream sets.
That helper was retired. All shared aliases now resolve to one accepted fork
artifact; the static archive matches its original accepted build. The old
profiled archive was quarantined outside the sysroot pending a proper rebuild.

The artifacts come from EmberBSD commit
`cffffd40b995ee0c1ada70d6f4c156409b22bae5`, built with GCC 12.5 on Zero 3W.
They are not a new GCC16 build of libc. The OS owns their
[source repair and original acceptance](https://github.com/oxtech-ember/EmberBSD/blob/main/common/lib/libc/arch/aarch64/atomic/docs/aarch64-outlined-cas.md).

| Artifact | SHA256 |
| --- | --- |
| Shared libc | `5dff821f1a1b42845e642cedd16375b310b78d04fa624bb21472d33b0fc14130` |
| Static libc | `be6a1144daa7d63c9c22dbd6c4bbe647d7d8dcc69a17deebe4d63395f4375cf6` |

The existing OS CAS regression was freshly cross-compiled with GCC 16.2.
The same objects were statically linked once to the repaired archive and once
to the old archive. On EmberBSD/CM5, the repaired executable passed all 850
checks across 20 variants; the old archive produced 140 failures. Link maps
identify the selected archives. Temporary execution preserved source hashes
and removed its remote files. No base installation or reboot was performed.

This establishes the repaired static provider and consistent shared aliases.
Eight sampled base headers matched the inspected fork. That repair did not
rebuild the entire header tree and base userland together. Its existing SDK
remains separate from the newer pinned snapshot above. Public binary release
of that snapshot remains pending. Neither receipt establishes GPU/NPU acceleration.
