# EmberBSD AArch64 target guest

This recipe runs installed-library and GI queries in a real EmberBSD guest.
It uses an accepted fork kernel and base. It installs no compiler in the guest.
The default guest has 1 GiB RAM, two virtual CPUs and a 384 MiB sparse FFS image.
Use a larger image for package acceptance.

## Host and inputs

Use native CPython 3.15, OpenSSH, QEMU AArch64, and fork-built NetBSD host tools.
Select a clean SDK source with host API 1 and `PROCESS_IDENTITY_API = 1` through
`--sdk-source`. The controllers use Python's standard library and the selected
SDK. They do not require Ruby, pip, a virtual environment or GNU timeout.
The query profile passed the execution checks on Darwin. The Linux backend
remains implemented; a native Linux run is a separate qualification gate.

The NetBSD tool directory must contain `nbmakefs`, `nbmtree`, `nbpwd_mkdb`,
`nbmkubootimage`, `aarch64--netbsd-objcopy` and `aarch64--netbsd-readelf`.
Use a verified base extraction and its matching fork source revision.
The builder hashes each selected base file. It reads devices, groups and
configuration from that exact Git revision. Verify the base archive provenance
before extraction. A directory name does not establish provenance.
Keep the extraction and new work on the same filesystem for hardlinks.

Set `EMBERBSD_BASE_REVISION` to the full source commit and
`EMBERBSD_KERNEL_SHA256` to the compressed kernel SHA256:

```sh
python3.15 build.py --sdk-source /absolute/SDK \
  /absolute/base /absolute/kernel.gz /absolute/os-source \
  /absolute/host-tools /absolute/new-private-work
python3.15 run.py --sdk-source /absolute/SDK /absolute/new-private-work \
  > /absolute/console.log 2>&1
```

The runner stays active until the guest stops. Select a native ELF or Mach-O
QEMU executable with `QEMU_AARCH64`. Configure its native library loader before
launch when the executable needs external libraries. `EMBERBSD_QUERY_QEMU_DATA`
can select its firmware/data directory. These settings do not permit target
objects to use the host compiler.

The kernel conversion follows the fork `mk.generic64` ARM64 Image recipe.
The guest uses `ld4` and `plcom0`. Its PCI network adapter has no PXE ROM because
it boots the supplied kernel directly. Networking uses QEMU's user network;
the SSH forward binds only to `127.0.0.1`.

Set these values before building. The builder records them; the runner validates
the recorded values. Older manifests keep the original RAM/CPU defaults.

| Setting | Default | Accepted range |
| --- | ---: | ---: |
| `EMBERBSD_QUERY_RAM_MIB` | 1024 | 1024–8192 |
| `EMBERBSD_QUERY_CPUS` | 2 | 1–8 |
| `EMBERBSD_QUERY_DISK_MIB` | 384 | 384–16384 |
| `EMBERBSD_QUERY_FREE_INODES` | 16000 | 16000–1000000 |
| `EMBERBSD_QUERY_PORT` | 22614 | 1024–65535 |

`nbmakefs -Z` creates a sparse image. The inode value is the additional reserve.
Run `python3.15 check-resources.py` for default, boundary and invalid-input checks.

## Full base staging

The default `query` profile selects a small runtime from a verified extraction.
Use `--base-profile full --base-sha256 SHA256` with the matching base set archive
for complete base userland. The archive must come from the same fork revision
as `EMBERBSD_BASE_REVISION` and the accepted kernel. The builder verifies the
archive SHA256. It does not establish the archive's build provenance for you.
Do not supply a compiler set or a package tree as the base input.

```sh
python3.15 build.py --sdk-source /absolute/SDK \
  --base-profile full --base-sha256 BASE_ARCHIVE_SHA256 --stage-only \
  /absolute/base.tar.xz /absolute/kernel.gz /absolute/os-source \
  /absolute/host-tools /absolute/new-private-staging
```

`--stage-only` prepares files and `artifacts/staging.json`. It does not create an
image or a runnable manifest. Use a different new work directory and omit this
flag to build an image. Resource settings remain the same for both profiles.
For a large runtime acceptance image, select 16384 MiB disk, 8192 MiB RAM,
four CPUs and 100000 additional free inodes before building.

Full mode exports a bounded set of make and configuration sources from the
selected Git revision. It invokes the source `distrib-dirs` and
`install-etc-files` targets with private object and temporary directories.
It requires `nbmake`, `nbawk`, `nbcat`, `nbsed` and `aarch64--netbsd-install`
in addition to the tools above. It builds no target program. It preserves all
base files, target ownership, set-ID modes and hardlinks. The host staging tree
has no target set-ID bits; mtree supplies those bits to the image.

The image keeps source-owned boot scripts, accounts and PAM configuration.
It adds key-only user `ember` with UID/GID 1000 and SSH alias `ember-e14-runtime`.
The existing root alias stays available for package installation and checks.
Both SSH aliases require the pinned host key. SSH disables password authentication
and PAM, as in the query profile. The full profile mounts ptyfs and mode-1777
tmpfs instances at `/tmp` and `/var/shm`. It enables no display manager.

Run `python3.15 check-full-base.py /absolute/new-fixture` for archive, ownership,
hardlink and account guards. The existing runtime `check.py` uses the recorded
full-base archive and payload hashes for full mode. Offline staging and metadata
checks do not establish a successful boot, normal-user login or GUI operation.
Add runtime packages and test those operations separately. Do not install guest
compilers or development toolchains for acceptance.

## Image and metadata

The query profile hardlinks immutable base files into a private staging tree.
Do not edit those files or change their permissions. It includes base Citrus modules,
encoding data and locales without static archives. The FFS image is a separate
writable file. The source sysroot stays unchanged.

Selected base commands include package tools, ownership and payload checks,
`ktrace`, `kdump`, `ps`, `fstat`, SSH and the target query prerequisites.
The private staging root stays mode `0700`. Image `/` uses the pinned fork's
`root:wheel` (`0:0`) and mode `0755`. The builder rejects missing, duplicate or
incompatible root metadata. It assigns image `fstat` to `root:kmem`, mode `02555`,
without changing the hardlinked base input. The group comes from pinned source.

```sh
python3.15 check-metadata.py --sdk-source /absolute/SDK \
  /absolute/base /absolute/os-source FULL_REVISION \
  /absolute/host-tools /absolute/new-metadata-work
```

This regression writes four finite FFS2 images with the real fork host tools.
It compares baseline and corrected root/fstat inodes, checks four invalid source
variants, and verifies unchanged base bytes, modes, ownership and private staging.
It does not execute target programs.

## SSH and execution checks

The private work contains client and host keys. Keep it outside Git and public
archives. Its SSH wrapper pins the generated host key, selects one client
identity and disables global known-host files. The guest permits key-only root
login. It mounts real ptyfs and uses the canonical `ptmx` device.

```sh
/absolute/work/bin/ssh ember-e14-query 'uname -a; df -ki /'
python3.15 check.py --sdk-source /absolute/SDK /absolute/work \
  /absolute/Ports/profiles/common-graphics/recipes/devel/gobject-introspection/files/target-query.py \
  /absolute/host-tools/aarch64--netbsd-readelf
python3.15 check-stop-identity.py --sdk-source /absolute/SDK /absolute/work
```

Run these checks with one exclusive owner and no active query or transfer.
They execute the real fork shell. They verify base hashes, HOME/USER, PTY,
wrong-key refusal, status 0/1/37, literal arguments, remote cleanup and at least
16,000 free inodes. Literal arguments include whitespace, quotes, an empty string
and shell characters. Dump mode still rejects ordinary arguments. The identity
check alters recorded executable, exact argv and birth fields; each must be
refused before SSH while the correct guest stays alive. It restores the record.

Logs stay under `logs`. `artifacts/input.json` records base/configuration/kernel
hashes, SDK API/source identity and initial disk identity. `artifacts/run.json`
records exact QEMU argv, native birth identity, binary hash and SDK provenance.
`artifacts/acceptance.json` records execution results. Each acceptance attempt
keeps separate logs. The image changes during execution; its initial hash does
not describe its current state.

## GI configuration and lifetime

```sh
python3.15 configure-query.py --sdk-source /absolute/SDK /absolute/work \
  /absolute/query-build /absolute/target-sdk \
  /absolute/host-tools/aarch64--netbsd-readelf /absolute/new-query.json
export EMBERBSD_GI_QUERY_CONFIG=/absolute/new-query.json
export EMBERBSD_GI_PYTHON=/absolute/native/python3.15
export EMBERBSD_SDK_SOURCE=/absolute/SDK
export PATH=/absolute/work/bin:$PATH
```

The launcher checks target ELF identity and each provider. It transfers only the
query closure and removes its private guest directory after execution. Keep one
active owner for queries and package transfers. Record each transfer destination
and check capacity before transferring a package payload.

Stop with `python3.15 stop.py --sdk-source /absolute/SDK /absolute/work`.
The helper checks exact arguments, native birth and QEMU binary hash. It requests
an acknowledged guest halt and verifies process exit. Only its own SSH client
can be terminated on timeout; it never signals QEMU. SSH gets 35 seconds, then a
five-second termination grace and at most the remainder of the 45-second deadline
for pipe closure. Timeout retains the guest for inspection. Run
`python3.15 check-stop-timeout.py` for the causal bounded-pipe control.

Preserve source, receipts and required inputs before removing private work.
A running query guest is a reusable service. It does not qualify the full KiCad
application, display integration or a physical board.
