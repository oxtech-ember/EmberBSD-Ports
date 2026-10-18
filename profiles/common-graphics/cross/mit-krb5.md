# MIT Kerberos for GUI clients

The common graphics profile keeps MIT Kerberos 1.22.2nb2 and its GSS API.
GTK and Tk printing can use this provider through CUPS. Set `KRB5_DEFAULT=mit-krb5`
in the build configuration. This does not configure a realm or start a KDC.

The selected release archive comes from MIT. Its SHA256 is
`3243ffbc8ea4d4ac22ddc7dd2a1dc54c57874c40648b60ff97009763554eaf13`.
The recipe retains pkgsrc patches and the upstream thread-safe client library.
The optional LDAP backend keeps its existing option and dependency.

NetBSD ELF cross configuration uses real target compiler and linker checks for
constructor/destructor attributes and positional printf. Attribute and format
diagnostics are fatal. Native builds keep the upstream execution probes.
Unknown cross platforms still fail. These branches select a documented ABI;
compilation alone does not prove the target loader or printf semantics.

The exact upstream sentinel and sprintf/strcmp programs pass in the EmberBSD
AArch64 acceptance VM with the common GCC16 16.2.0 toolchain and fork sysroot.
Removing the attributes leaves both sentinels present. Seven real Autoconf
cases preserve the upstream cross refusal, patched cross success, native
behavior, unknown-platform refusal and two compiler diagnostic controls.

Cross packages use one runtime and one matching target SDK. The canonical
`security/mit-krb5` package retains libraries, plugins, client/server commands,
runtime manuals, examples and translations. `security/mit-krb5-devel` contains
headers, static libraries, libtool and pkg-config metadata, `krb5-config` and
`compile_et`. Install both in the development-host sysroot. Install only the
runtime on the target. Native builds keep their complete original package.

Both ordinary cross recipes stage the full upstream installation. Explicit
packing lists define an exhaustive, disjoint partition. The selector verifies
all files and links before removal. It rejects aliased staging parents,
unlisted or missing files, unsafe links and runtime links through SDK files.
The installed `compile_et` uses target AWK/SED paths; its build-time generator
continues to use native tools. No target generator runs during the build.

Set the host Python 3.15 executable through `EMBERBSD_CROSS_BUILD_PYTHON`.
Set the explicit SDK API 1 source through `EMBERBSD_SDK_SOURCE`.
The controller requires only the Python standard library and the SDK modules.
Its thin policy wrapper requires `emberbsd_sdk.stage.STAGE_PARTITION_API = 1`.
The shared SDK mechanism owns inventory validation and pruning.

The full native GCC16 source package passes normal package checks. Its API consumer
passes four concurrent principal/cache/AES lifecycles, modified-ciphertext
rejection and GSS mechanism/name operations. GCC16 path analysis, Clang 19
analysis and Cppcheck 2.22 pass for this consumer. Strict native Memcheck reports
no invalid access or lost blocks, but retains 4,648 bytes in 37 process-global
blocks. The upstream Linux `LIB_UNLOAD_PREVENTED` policy omits their finalizers.
This is not a clean whole-library memory result.

The libtool link also preserves the upstream NetBSD/Linux GNU ELF `nodelete`
policy. Upstream disables global finalizers for this policy. The original
pkgsrc link lost the flag. A real native GSS `dlopen`/`dlclose` control fails
without it and passes with it. ELF `NODELETE` and `RTLD_NOLOAD` verify the result.
The nb2 ordinary packages and installed target API acceptance remain pending.
The default LDAP-disabled build does not establish LDAP backend execution.
Realm authentication, credentials, network KDC service and CUPS integration
remain separate acceptance tasks.

The reproducible contracts are in [tests/mit-krb5](../tests/mit-krb5).
Pass `--sdk-source /absolute/SDK` to each Python command. `configure-contract.py`
requires original and patched upstream source directories, GCC16 native and
cross compilers, the sysroot, Autoconf and unused work. `stage-contract.py`
requires the real complete stage and its three normalized packing lists.
`prepare-client.py` requires the installed runtime/SDK pair and produces a
bounded target bundle. Verify its archive hash before running `sh run.sh`.
