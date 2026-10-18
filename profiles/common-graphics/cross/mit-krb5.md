# MIT Kerberos for GUI clients

MIT Kerberos 1.22.2nb2 provides the common thread-safe GSS client API for GUI
printing dependencies. Normal GCC16 packages pass on Linux amd64 and for the
EmberBSD AArch64 sysroot. Installed target API and loader checks pass in the
acceptance VM. Realm authentication and CUPS printing remain separate checks.
See the [measured receipt](mit-krb5-linux-aarch64.json).

The selected release archive comes from MIT. Its SHA256 is
`3243ffbc8ea4d4ac22ddc7dd2a1dc54c57874c40648b60ff97009763554eaf13`.
The recipe retains pkgsrc patches and enables the upstream thread-safe client
library. The optional LDAP backend keeps its existing option and dependency.
Set `KRB5_DEFAULT=mit-krb5` to select the provider. This does not configure a realm.

NetBSD ELF cross configuration uses real target compiler and linker checks for
constructor/destructor attributes and positional printf. Attribute and format
diagnostics are fatal. Native builds keep the upstream execution probes.
Unknown cross platforms still fail. The exact upstream sentinel and
sprintf/strcmp programs pass on the fork ABI with common GCC16 16.2.0.
Removing the attributes leaves both sentinels present. Seven real Autoconf
cases also preserve native behavior and reject missing or incorrect capabilities.
Compilation alone does not prove the target loader or printf semantics.

The libtool link retains the upstream NetBSD/Linux GNU ELF `nodelete` policy.
Upstream disables global finalizers for this policy. A genuine GSS
`dlopen`/`dlclose` control reproduces the missing protection without the flag.
The repaired package passes both ELF `NODELETE` and `RTLD_NOLOAD` checks.
The same loader control passes after a normal target package upgrade.

Cross packages use one runtime and one matching target SDK:

- `security/mit-krb5` retains libraries, plugins, client/server commands,
  runtime manuals, examples and translations. Its archive has 101 entries.
- `security/mit-krb5-devel` retains headers, static libraries, libtool and
  pkg-config metadata, `krb5-config` and `compile_et`. Its archive has 91 entries.

Install both in the development-host sysroot. Install only the runtime on the
target. Native builds keep their complete original package. Each ordinary
cross recipe stages the complete upstream installation. Explicit packing lists
define an exhaustive, disjoint partition. The shared SDK partition mechanism
verifies inventory, root identity and link ownership before removal.
Ten real-stage controls include missing files, overlaps, unsafe links and
aliased-parent refusal with no partial deletion.

The installed `compile_et` embeds `/usr/bin/awk` and retains ordinary target
PATH lookup for `sed`. Build-time generators keep native tools. No target
generator runs during the build. Set the host Python 3.15 executable through
`EMBERBSD_CROSS_BUILD_PYTHON` and explicit SDK source through `EMBERBSD_SDK_SOURCE`.
The thin policy wrapper requires SDK API 1 and `STAGE_PARTITION_API = 1`.
It uses only the Python standard library and shared SDK modules.

All three packages pass packing-list, interpreter, permission, RELRO, RPATH and
work-reference checks; the cross packages also pass PIE checks. The SDK readback
verifies all 101 runtime and 91 SDK entries. On the unprivileged build host,
`ksu` keeps identical bytes while ownership normalization removes its SUID bit.
The normally installed target file is `root:wheel`, mode `4555`.
No host mode repair or permission-check bypass is used.

The installed target consumer verifies five real library hashes and passes
four concurrent principal/cache/AES lifecycles, modified-ciphertext rejection,
and GSS mechanism/name operations. It uses GCC16 UBSan traps. Dependencies are
not sanitizer-instrumented. Normal runtime upgrade and `pkg_admin` checks pass
for the final VM catalog of 20,111 files from 81 packages. The target has neither
`compile_et` nor `krb5-config`; no MIT daemon was enabled.

GCC16 path analysis, Clang 19 analysis and Cppcheck 2.22 pass for the consumers.
Strict native Memcheck reports no invalid access or lost blocks. It exits 99
because 4,648 bytes in 37 process-global blocks remain reachable under the
upstream `LIB_UNLOAD_PREVENTED` policy. There are no suppressions. This is not
a clean whole-library memory result. Target Valgrind was not run.

The reproducible contracts are in [tests/mit-krb5](../tests/mit-krb5).
Pass `--sdk-source /absolute/SDK` to each Python command. `configure-contract.py`
uses original and patched sources, GCC16 native/cross compilers, the sysroot,
Autoconf and unused work. `stage-contract.py` uses the real complete stage and
its three normalized packing lists. `prepare-client.py` consumes the installed
runtime/SDK pair. Verify its archive hash before running `sh run.sh` on target.
LDAP backend execution, real realm credentials, authenticated printing,
amd64 target execution and physical GUI/CAD acceptance remain unverified.
