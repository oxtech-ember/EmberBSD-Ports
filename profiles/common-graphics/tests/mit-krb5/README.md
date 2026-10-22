# MIT Kerberos contracts

## Cross-build client keytab default

Run `default-client-keytab.py` after pkgsrc extracts and patches the MIT source.
Pass the target `MIT_KRB5_STATEDIR` value from `bmake -v MIT_KRB5_STATEDIR`
in the configured target package context.
The check executes only the generated Autoconf default-selection block with a
fake build-host `krb5-config`. It checks that cross builds use the target path
and that the upstream host default remains unchanged.

```sh
python3.15 -E -S profiles/common-graphics/tests/mit-krb5/default-client-keytab.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --source /absolute/krb5-1.22.2/src \
    --recipe /absolute/pkgsrc/security/mit-krb5/Makefile \
    --target-statedir /var --work /absolute/new-keytab-work
```

This is a source-level configure-policy check. It does not compile or run
target code.

These host checks use CPython 3.15 and an explicit SDK source. They require
SDK API 1. The metadata check also requires producer stream and inspection
API 1. No pip packages are required.

## Installed metadata generation

Run `rpath-contract.py` with common GCC16 native and cross compilers. Select
the same target sysroot used by the ordinary package. Read the expanded target
`COMPILER_RPATH_FLAG` with `bmake -v COMPILER_RPATH_FLAG` in that configured
recipe. Pass the value with `--rpath-flag=VALUE`.

```sh
python3.15 -E -S profiles/common-graphics/tests/mit-krb5/rpath-contract.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --archive /absolute/krb5-1.22.2.tar.gz \
    --pkgsrc /absolute/exported-pkgsrc \
    --bmake /absolute/bin/bmake --autoconf /absolute/bin/autoconf \
    --cc /absolute/toolchain/bin/aarch64--netbsd-gcc \
    --native-cc /absolute/bin/gcc-16 --sysroot /absolute/target-sysroot \
    --rpath-flag=VALUE --work /absolute/new-metadata-work
```

The native compiler must link and run its ordinary Autoconf checks. If its
configured platform SDK is unavailable, pass the installed native SDK with
`--native-sysroot /absolute/native-sdk`. This option never selects target headers.

The check verifies the MIT archive SHA256. It extracts only the real library
policy macros, config inputs and complete `krb5-config` template. It applies the
selected ordinary recipe patches with zero fuzz. It reconstructs the inherited
baseline and verifies its historical pkgsrc patch digest. The candidate uses
the recipe's declarations and the actual pkgsrc `mk/subst.mk` implementation.
The selected upstream `KRB5_AC_CHOOSE_ET` and `KRB5_BUILD_PROGRAM` macros generate
both scripts through Autoconf. This is a selected macro contract, not the complete
MIT configure or package build.

The original target script must emit its unresolved compiler variable. Its
consumer link must fail on that literal argument. The repaired script must
produce the expanded compiler flag. An unchanged installed-API consumer must
link with GCC16 and retain the target GSS provider and runtime search path.
Before and after native script output must match exactly.

The measured native baseline uses Darwin. Other native platforms, DragonFly
and Solaris execution remain unverified. The check supports common AArch64
and amd64 compilers; the measured target link uses AArch64. It does not run the
consumer, rebuild/install packages or accept realm authentication or printing.
It reuses unchanged, previously analysed `client.c`. This metadata change adds
no C source. Keep receipts and incomplete work until their inputs are preserved.
A producer ownership refusal leaves `producer-ownership-unconfirmed`; do not
reuse or remove that work until the producer is resolved.
