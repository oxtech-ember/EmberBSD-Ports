# Mozilla root certificates in a compiler SDK

The compiler SDK supplies EmberBSD headers, libraries and the dynamic loader.
Its build runs `tools` and `libs`. It does not build a complete base userland.
An absent `/bin/echo` or `/usr/bin/awk` in that SDK does not identify the
installed target's base utilities. Its METALOG cannot prove those executables.

For cross builds that select NetBSD 11, `security/mozilla-rootcerts` has two
explicit roles. Native tools extract the pinned certificate data on the build
host. The installed script uses the NetBSD 11 full-base runtime contract.
The recipe does not change the generic `USE_TOOLS+=tool:run` refusal rules.
Other tools, targets and missing packaged Bash/Perl runtimes remain checked.
Native builds retain their original tool and substitution behavior.

The build needs host awk and OpenSSL 3.6.5 from the ordinary pkgsrc host-tool
dependency. It passes those tools through the upstream script's `AWK` and
`OPENSSL` environment API. It does not execute a target program on the host.

The installed script uses `/bin/sh`, `/usr/bin/awk` and the `/bin/echo`,
`expr`, `ln`, `ls`, `mkdir` and `rm` utilities. It also uses the normal base
`cat` command. With target builtin OpenSSL, the script uses `/usr/bin/openssl`.
With pkgsrc OpenSSL, it uses `${PREFIX}/bin/openssl` and has an explicit target
`openssl>=3.6.5` dependency. The host formatter dependency remains separate.
This contract requires a target with the normal NetBSD 11 full base.
It does not describe an appliance image that omits these commands.

The source contract is pinned to EmberBSD commit
[`32afa976de8d28799739978f80cc3fca08928145`](https://github.com/oxtech-ember/EmberBSD/tree/32afa976de8d28799739978f80cc3fca08928145).
The base [bin install rule](https://github.com/oxtech-ember/EmberBSD/blob/32afa976de8d28799739978f80cc3fca08928145/bin/Makefile.inc)
sets `BINDIR=/bin`. Each listed `bin/TOOL/Makefile` sets its matching `PROG`.
The [awk recipe](https://github.com/oxtech-ember/EmberBSD/blob/32afa976de8d28799739978f80cc3fca08928145/external/historical/nawk/bin/Makefile)
and [OpenSSL recipe](https://github.com/oxtech-ember/EmberBSD/blob/32afa976de8d28799739978f80cc3fca08928145/crypto/external/apache2/openssl/bin/Makefile)
set their program names and `/usr/bin` install directories.
Source declarations, package construction and execution on a target have
separate acceptance boundaries. A target VM can have a different recorded
OS revision. Its binaries must not be copied into the compiler SDK.

Run the causal check with the previous and updated exported pkgsrc trees,
the real compiler SDK, staged script and pinned source data:

```sh
python3 profiles/common-build-tools/tests/rootcerts-tools.py \
    --pkgsrc /absolute/new-export --baseline-pkgsrc /absolute/old-export \
    --makeconf /absolute/cross.mk.conf --sysroot /absolute/compiler-sysroot \
    --bmake /absolute/host/bin/bmake \
    --staged-script /absolute/stage/usr/pkg/sbin/mozilla-rootcerts \
    --certdata /absolute/certdata-20260715.txt \
    --os-source /absolute/EmberBSD --os-commit 32afa976de8d28799739978f80cc3fca08928145 \
    --work /absolute/new-check
```

The check verifies the SDK's source pin, full-base install declarations,
actual native/cross pkgsrc metadata and the installed script. It also runs
a real host extraction. Target acceptance must verify base command hashes
and run extraction, rehash and installation only in an owned temporary
prefix. It must preserve the target's real `/etc/openssl` configuration.

The target-side check accepts an extracted package prefix and a new private
work directory. Supply the expected script and certificate-data SHA256 values.
It records base command hashes, runs the real installed script, checks all PEM
certificates and rehash links, and compares the private install with extraction:

```sh
sh profiles/common-build-tools/tests/rootcerts-runtime.sh \
    /absolute/temporary/pkg /absolute/temporary/new-check \
    SCRIPT_SHA256 CERTDATA_SHA256
```

The target-side check leaves its output for the caller's receipt. After saving
and verifying that receipt, remove only the caller's owned temporary prefix.

A minimal query guest can omit OpenSSL, echo, expr and ln. In that guest,
an optional fifth argument selects a separately verified tools prefix.
It must contain `bin/openssl`, `bin/echo`, `bin/expr`, `bin/ln` and their
matching library closure in `lib`. Use executables and libraries from the
same pinned base as the guest. Verify their hashes before and after transfer.
The test uses the upstream environment APIs and an isolated loader path.
This mode checks the script API. It does not accept the guest's default
full-base paths. Keep that distinction in the execution receipt.

The ordinary GCC16 AArch64 package `mozilla-rootcerts-1.1.20260715nb2.tgz`
passes checksum, static packing-list, interpreter, permission and work-reference
checks. Its SHA256 is
`f824c5dcd4c7a1cd5e143dabf57df9c5617a1a2c52be26c300d020488f1aaedd`.
All host/bootstrap and target dependencies were already installed.
No target package installation was part of that build.
The causal regression passes nine groups, including exact native metadata
comparison, strict generic guards, source install paths and real host
extraction of 121 certificates. An inherited group-writable host volume
ancestor reports one permission warning. Package permissions have zero errors.

The installed script API also passes extraction of 121 certificates,
121 live rehash links and an identical private-prefix installation on an
EmberBSD AArch64 query guest. Each extracted PEM parses with real OpenSSL.
A bad expected script hash fails before the test creates its work directory.
The guest lacks some default full-base commands. The API test supplies four
commands and their library closure in its private prefix. Those bytes and
links match the qualified base archive at OS commit
`6dd57144183678938164b4c2dcfc370cdbde8473`, with base archive SHA256
`688dc6701cd83283d1287fc18dee8b9af35f067096cdd4a92de7e0593fdacddb`.
The six existing guest commands also match exact qualified archive members,
the guest input inventory and the actual execution hash witness.
Transfer hashes pass before and after execution. The temporary remote prefix
is removed and its absence is checked. The compiler SDK is unchanged.
This is script environment-API acceptance on a minimal guest. Default full-base
command presence and normal package activation/removal remain separate gates.

## Native SDK trust store

The Darwin GCC16 foundation includes the existing
`security/mozilla-rootcerts-openssl` package. Its dependency uses the same pinned
Mozilla certificate data as other consumers. OpenSSL comes from Ports, and
its configuration base is `${LOCALBASE}/etc` in this producer.

The adapter keeps `PREFIX` when its configuration directory is inside that
prefix. Its packing list then uses relative `etc/openssl/certs` paths. Builtin
OpenSSL and explicitly external configuration directories keep the earlier
root-prefix behavior. The adapter still stages all certificate files through
`DESTDIR`. The existing packing list owns the PEM files, hash links and bundle.
It does not create, replace or remove `etc/openssl/cert.pem`.

OpenSSL uses the hashed `etc/openssl/certs` directory as its standard `capath`.
Python can therefore report `cafile=None` and still verify HTTPS correctly.
Do not copy a host CA file or disable certificate verification to accept this
package. After normal package installation, run the runtime check with the
installed SDK Python and no `SSL_CERT_FILE` or `SSL_CERT_DIR` overrides:

```sh
/absolute/sdk/bin/python3.15 profiles/common-build-tools/tests/rootcerts-prefix-runtime.py \
    --prefix /absolute/sdk --url https://github.com/
```

The source regression `tests/rootcerts-prefix.py` preserves the install commands
and packing-list ownership. Supply `--make-arg` for each SDK make command word
and `--work` for a new absolute directory to check finite recipe metadata.
It covers contained, external, neighboring and builtin paths. The previous
recipe and two mutations prove the prefix and relative-packing-list failures.
These source and metadata checks do not build or install a package. Installed
package lifecycle and the verified HTTPS request remain separate acceptance gates.
