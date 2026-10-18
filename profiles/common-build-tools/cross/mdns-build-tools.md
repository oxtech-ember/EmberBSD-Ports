# mDNSResponder target selection and build tools

The common pkgsrc patch corrects the existing
`net/mDNSResponder` 2559.1.1 recipe at revision 2. Its source is Apple's
[2559.1.1 tag](https://github.com/apple-oss-distributions/mDNSResponder/tree/mDNSResponder-2559.1.1).
The source archive SHA256 is
`f3c4d25c572ae6e64e42e906672d410898fd3f3c59ed538d46c20de8d7725ed0`.
The original pkgsrc patch inventory, licenses, IPv6 selection and installed
package list remain intact.

This is a scoped correction to the existing pkgsrc source pin. Apple also
publishes the newer [2881.120.11 tag](https://github.com/apple-oss-distributions/mDNSResponder/tree/mDNSResponder-2881.120.11),
at commit `641cdf73ef46e1824895cbc44ad8ac7647da2479`.
This check does not qualify that release or establish continued upstream
support for 2559.1.1. A source update needs separate package and consumer checks.

The upstream POSIX Makefile runs `uname` and assigns `os=linux` or `os=x`.
Those assignments override the recipe's environment value. On a Linux host,
the former NetBSD cross recipe therefore compiles the Linux source branch.
The recipe now passes all existing platform mappings through `MAKE_FLAGS`.
GNU Make command arguments retain the selected target OS.

Flex and Bison generate the `dnsextd` lexer and parser. The upstream default
graph selects `dnsextd` only for Darwin. NetBSD's default graph builds the
DNS-SD library, daemon and clients directly from C sources. The recipe now
requires Flex and Bison only for Darwin. This avoids pkgsrc's implicit target
Flex library dependency for the NetBSD package. The generator rules and Darwin
selection remain intact. Explicit upstream `dnsextd` builds still need both
generators and are outside the NetBSD package's installed interface.

The [regression](../tests/mdns-build-tools.py) uses Python 3.15 and SDK library
API 1. It queries the real pkgsrc metadata before and after the exact common
patch. It checks NetBSD, Linux and Darwin tool selection, including the former
Flex buildlink dependency. Upstream GNU Make dry runs reproduce host OS
selection and check the complete NetBSD graph. Separate Darwin and explicit
`dnsextd` dry runs retain both generator commands.

```sh
python3.15 profiles/common-build-tools/tests/mdns-build-tools.py \
  --sdk-source /absolute/EmberBSD-SDK \
  --pkgsrc /absolute/prepared-pkgsrc \
  --archive /absolute/mDNSResponder-2559.1.1.tar.gz \
  --makeconf /absolute/private-cross-mk.conf \
  --bmake /absolute/native-bmake --gmake /absolute/native-gmake \
  --work /absolute/new-check-directory
```

The Linux-host check passes against the pinned pkgsrc recipe. It records the
SDK commit, consumed module hashes, archive/patch hashes, commands and statuses.
It accepts the original recipe or this exact repaired recipe. It rejects an
unrelated version. The metadata and dry runs do not establish a Darwin build.

An isolated ordinary AArch64 package passes with GCC16 and one build job.
All installed files pass package-list, PIE, RELRO, runtime-path and work-reference
checks. The package retains `dns-sd`, four standalone clients, `mdnsd`,
`libdns_sd`, the public header and both manual pages. No package is installed
by this check. Installed DNS-SD discovery, daemon operation, CUPS integration
and target memory checks remain separate acceptance work.
