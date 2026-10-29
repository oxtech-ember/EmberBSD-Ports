# ICU runtime and development-host SDK

The common `textproc/icu` recipe provides ICU 79.1 and the complete applicable
Ports patch set. Native packages include ICU libraries, data and host generators.
For NetBSD cross builds, `icu` contains the runtime libraries and user commands;
`icu-devel` contains the headers, static libraries, generator tools and build
metadata needed in the development-host sysroot. The SDK package depends on
the exact matching runtime package. AArch64 and amd64 use the same source and
patch set.

Cross builds use native ICU generators of the same release and the explicitly
selected Python 3.15 and SDK source. The SDK stage partition checks the complete
installed payload against the runtime and development manifests before selecting
either package. The target runtime does not contain the development headers or
generators.

`tests/icu-stage-policy.py` checks the package split using an actual complete
stage. `tests/icu-cross-metadata.sh` checks the generated host-tool and target
metadata. `tests/icu-fixtures.py` generates resources with the selected native
ICU, and `tests/icu-cross-consumer.sh` builds the target consumer. Run the
resulting `icu-installed.sh` on the target to check conversion, collation and
resource loading; a host build does not establish target runtime acceptance.

The source configure step leaves Python empty to avoid a bootstrap dependency
cycle. The upstream data test receives the selected host interpreter through
`ICU_TEST_PYTHON` and `TEST_MAKE_FLAGS`; the installed runtime does not depend
on that interpreter.
