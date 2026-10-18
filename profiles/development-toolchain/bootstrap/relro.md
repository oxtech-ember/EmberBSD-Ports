# Relink the GCC16 runtime with RELRO

The runtime-only nb3 package requires a nonempty `PT_GNU_RELRO` segment.
The ordinary pkgsrc RELRO check remains enabled. Future full bootstraps pass
`-Wl,-z,relro` to all target runtime links. The default partial RELRO policy
does not require `-z,now`.

`relink-relro.py` supports the completed standalone locale rebuild. It uses
the authenticated original bootstrap archive to relink exactly `libgcc_s.so.1`,
`libgomp.so.1.0` and `libatomic.so.3.0`. It does not compile these libraries again.
It retains the newly compiled libstdc++, its headers and the original CRT/static
support files byte-for-byte. It does not edit ELF output after linking.

Run the helper with the original bootstrap and locale work paths:

```sh
python3 -B profiles/development-toolchain/bootstrap/relink-relro.py \
    aarch64 /absolute/locale-pkgsrc /absolute/original-pkgsrc \
    /absolute/gcc-16.2.0.tar.xz /absolute/application-toolchain \
    /absolute/emberbsd-sysroot /absolute/original-runtime-work \
    /absolute/locale-runtime-work /absolute/original-bootstrap-backup.tgz \
    BACKUP_SHA256 /absolute/new-relro-work
```

The backup must be the verified full original bootstrap archive. It must retain
the original work basename, genuine driver/link tools, objects, version maps,
configuration and source receipts. The original seed and linker paths must
still exist and match their recorded hashes. The helper restores only selected
inputs. Receipt input paths are canonical absolute paths; verification does not
depend on the caller's working directory. It executes the archived upstream
link commands with the original
driver and linker. A baseline must reproduce each accepted DSO byte-for-byte.
The second link changes only its output path and adds `-Wl,-z,relro`.

The helper compares every defined dynamic symbol's name/version, size, type,
binding and visibility. SONAME and dependencies must remain unchanged.
The stock pkgsrc script must report all three missing baseline segments and
no missing final segment. All ordinary runtime stage checks then run.
The AArch64 nb3 result passes these gates, normal pkgsrc packaging, SDK
replacement and [installed VM checks](../runtime/README.md#aarch64-installed-acceptance).
The target result covers an upgrade; nb3 removal/reinstallation remains pending.
The helper uses about
85 MiB for selected inputs, proof DSOs and the assembled development stage.

`relink.json` separates the freshly compiled locale parent from the three
relinked DSOs. Final inventory permits only those three regular-file changes.
The original nb2 identity and locale-parent receipts remain unchanged.
The parent work path, archive, selected input files and logs remain required
for verification. Retain them until package and consumer acceptance finish.
The development stage remains partial; preserve the existing SDK linker
aliases, OpenMP headers and specs during coordinated import.

Historical provenance verification is an internal operation. It cannot install
or create packages and has no CLI or environment bypass. Normal verification
rejects missing, empty or unmapped RELRO segments. Host tests exercise those
refusals, changed parent/input/output receipts and unowned stage changes.
These synthetic test fixtures do not establish a target build or runtime result.
