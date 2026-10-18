# EmberBSD AArch64 query guest

This recipe runs small installed-library and GI queries in a real EmberBSD guest.
It uses an accepted fork kernel and base sysroot. It does not install compilers.
The default guest has 1 GiB RAM, two virtual CPUs and a 384 MiB sparse FFS image.
Use a larger image for the full KiCad package and its data.

## Inputs

Use a Linux host with Ruby, OpenSSH, QEMU AArch64, GNU `timeout` at
`/usr/bin/timeout`, and fork-built NetBSD host tools.
The tool directory must contain `nbmakefs`, `nbmtree`, `nbpwd_mkdb`,
`nbmkubootimage`, `aarch64--netbsd-objcopy` and `aarch64--netbsd-readelf`.
Use a verified base extraction and its matching fork source revision.
The builder hashes every selected base file. It reads device definitions,
the full group database and other configuration from that exact Git revision.
The caller must first verify the base archive provenance; a directory name does
not establish it.

Set `EMBERBSD_BASE_REVISION` to the full source commit and
`EMBERBSD_KERNEL_SHA256` to the compressed kernel SHA256. Then run:

```sh
ruby build.rb /absolute/base /absolute/kernel.gz /absolute/os-source \
  /absolute/host-tools /absolute/new-private-work
ruby run.rb /absolute/new-private-work > /absolute/console.log 2>&1
```

Run QEMU as a persistent task process. The second command remains active.
The kernel conversion follows the fork `mk.generic64` ARM64 Image recipe.
The guest uses the kernel's `ld4` and `plcom0` devices. The PCI network adapter
has no PXE option ROM because this guest boots the supplied kernel directly.

`nbmakefs -Z` creates a sparse image from the start. `-f 16000` reserves at least
16,000 inodes beyond the installed base. Set `EMBERBSD_QUERY_DISK_MIB` (384 to
16384) and `EMBERBSD_QUERY_FREE_INODES` (16000 to 1000000) before building to
change these limits. `EMBERBSD_QUERY_PORT` defaults to 22614.
Set `EMBERBSD_QUERY_RAM_MIB` to a decimal integer from 1024 to 8192 before
building to select guest RAM. The default is 1024. The builder records this
value in `artifacts/input.json`; the runner validates and uses that value.
Older manifests without `ram_mib` retain the 1024 MiB default.
Run `ruby check-resources.rb` for read-only default, boundary and invalid-input checks.

The builder hardlinks immutable base files into a private staging tree. Do not
edit that tree's base files or change their permissions. It includes Citrus
modules, encoding data and locales from the same base, without static archives.
The generated FFS image is a separate writable file. The sysroot stays unchanged.
The selected base commands include package installation, deletion and integrity
tools, `cmp`/`readlink`/`mv` for payload checks, `ktrace`/`kdump`, and `ps`/`fstat` for process
and open-file inspection. Each comes from the same
verified base and has a recorded hash. No target compiler is added.
The image metadata assigns `fstat` to `root:kmem` with mode `02555`.
The builder resolves `kmem` from the accepted source group database; it does
not change the hardlinked base file. Run
`ruby check-fstat-metadata.rb BASE SOURCE_ETC NETBSD_TOOLS NEW_WORK`
on the base filesystem for a small actual FFS2 check.
The two commands also passed execution with matching base library providers
in the E34 AArch64 guest. This does not qualify the complete KiCad application.

## SSH and acceptance

The private work directory contains generated client and host keys. Keep the
whole directory outside Git. Do not include keys or the guest disk in public
archives. SSH binds to `127.0.0.1` only. The private wrapper uses a pinned host
key, strict checking, one explicit client identity and no global known-host file.
The guest has key-only root login, real ptyfs and the canonical `ptmx` device.

```sh
/absolute/new-private-work/bin/ssh ember-e14-query 'uname -a; df -ki /'
ruby check.rb /absolute/new-private-work \
  /absolute/Ports/profiles/common-graphics/recipes/devel/gobject-introspection/files/target-query.rb \
  /absolute/host-tools/aarch64--netbsd-readelf
```

Run checks while the guest has one owner and no other query is active. The check
uses the real fork shell as its AArch64 executable. It verifies base command
hashes, HOME/USER, PTY allocation, a wrong-host-key refusal, exit codes 0/1/37,
top-level shell failure, literal argv and remote query cleanup. Arguments include
spaces, quotes, an empty string and shell metacharacters. Dump mode must still
reject ordinary arguments. The final inode check requires 16,000 free inodes.
No target compilation or mock target execution occurs in this check.

Logs remain under `logs` and the launcher cache. `artifacts/input.json` records
base/configuration/kernel hashes, initial image hash and allocated disk blocks.
`artifacts/acceptance.json` records actual acceptance results. The image changes
during execution, so its initial hash is not a current-state hash.

## GI integration and lifetime

Create a configuration with the actual query build directory and target SDK:

```sh
ruby configure-query.rb /absolute/new-private-work /absolute/query-build \
  /absolute/target-sdk /absolute/host-tools/aarch64--netbsd-readelf \
  /absolute/new-query.json
export EMBERBSD_GI_QUERY_CONFIG=/absolute/new-query.json
export PATH=/absolute/new-private-work/bin:$PATH
```

The canonical launcher verifies ELF identity and each library provider. It
transfers only the query closure and removes its private guest directory after
execution. Use one active owner for queries and package transfers. Root login
can receive a streamed tar payload; the caller must record its exact destination,
check free space first and remove only its own payload after acceptance.

To halt the guest, run `ruby stop.rb /absolute/new-private-work`. The helper
checks the recorded PID, process start time, QEMU file hash and complete arguments,
including the owned disk. It requests a graceful guest halt, requires a guest
acknowledgment and verifies process exit. Its receipt records these observations.
The owned SSH request has a 35-second timeout and a five-second kill grace period.
The whole stop attempt has a 45-second deadline. A timeout does not kill QEMU.
With exclusive guest ownership, run `ruby check-stop-identity.rb WORK` to check
that altered executable and process-start metadata are refused before SSH.
The check restores the original record and verifies that the correct guest lives.
It does not kill
unrelated processes or delete disks. Retain source and evidence before removing
private work. A running query guest is a reusable test service, not a completed
KiCad GUI or physical-board acceptance.
