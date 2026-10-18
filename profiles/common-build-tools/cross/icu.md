# ICU runtime and development-host SDK

The canonical `textproc/icu` recipe retains ICU 78.3, its complete data and
all installed features. It comes from pkgsrc commit
`fff4deb639a1a640476203c80f752fb77b6cb14b`, with the existing common cross
host-tool and installed-metadata repairs. The recipe retains all 18 actual
pkgsrc patches and their hashes. The imported distinfo removes one stale
checksum for `patch-i18n_measunit_extra.cpp`, which that commit does not contain.
The upstream source archive hashes are unchanged.

All complete common profiles, including `common-media` and `plasma-mobile`,
export this same recipe and its companion `textproc/icu-devel`.

| Build | Package | Installed role |
|---|---|---|
| Native | `icu-78.3nb1` | Complete ordinary package, including native generators |
| NetBSD cross | `icu-78.3nb2` | Versioned shared libraries, `icuinfo`, `uconv`, `derb`, their manuals and license |
| NetBSD cross | `icu-devel-78.3nb2` | Headers, static libraries, linker symlinks, generators, generator manuals and build metadata |

The SDK depends on exactly `icu-78.3nb2`. Consumers retain the ordinary ICU
runtime dependency. Cross buildlinks add `icu-devel` as a build-only dependency
and expose its complete development interface. Keep the SDK in the host
sysroot. Install the runtime package in the target image. The cross-only SDK
recipe rejects native packaging. Both AArch64 and amd64 have metadata support.

Both package roles build and install the full upstream source. They then
select an exhaustive partition from static PLISTs with `LIBTOOLIZE_PLIST=no`.
The full PLIST matches all 274 files and links from the complete GCC16
AArch64 install stage. Runtime owns 18 entries; SDK owns 256. No `.la` files
occur in that stage. All six shared-library families remain available.
The SDK owns the `lib/icu/current` directory link and the metadata it exposes.

Set `EMBERBSD_CROSS_BUILD_PYTHON` to Python 3.15 and set
`EMBERBSD_SDK_SOURCE` to an explicit SDK source tree. The SDK must provide
library API 1 and `emberbsd_sdk.stage.STAGE_PARTITION_API = 1`, including
directory-link support. Ports parses the generated package PLISTs and checks
ICU runtime policy. The shared SDK validates complete ownership, dependencies
and links before it removes any unselected file. An SDK link may refer to the
exact runtime dependency. Runtime links cannot depend on the SDK.

Run the policy regression on a complete installed payload before packaging:

```sh
python3.15 -B profiles/common-build-tools/tests/icu-stage-policy.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --full-stage /absolute/complete-stage/usr/pkg \
    --mh-name mh-bsd-gcc --work /absolute/new-policy-check
```

The regression copies the actual declared files. It checks both partitions,
their unchanged union and seven refusals before pruning: unknown role, unlisted
file, duplicate entry, leaked generator, missing file, missing SDK feature and
a boolean in place of the integer feature version.
The real native and AArch64 payload checks pass. Native metadata retains the
complete package; cross metadata selects the two roles and exact dependency.
These checks do not establish final split package or installed target acceptance.

Build resource fixtures with the matching native package on the development
host. Then build the consumer with the target SDK:

```sh
python3.15 -B profiles/common-build-tools/tests/icu-fixtures.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --native-prefix /absolute/native-prefix --work /absolute/new-fixtures
sh profiles/common-build-tools/tests/icu-cross-consumer.sh \
    /absolute/cross-tools /absolute/sysroot /absolute/new-fixtures \
    /absolute/new-consumer
```

Copy the consumer directory to EmberBSD and run `sh run.sh .`. The target
runner requires the runtime package and rejects installed ICU SDK files and
generators. It checks conversion, collation and consumption of host-generated
resources. Native `genrb` and `pkgdata` fixture generation passes. Final split
packages, installed lifecycle checks and amd64 execution remain separate gates.
