# Complete initial libnbcompat

The common recipe remains `pkgtools/libnbcompat`, version 20251029, revision 2.
It retains the complete canonical source, headers, DB implementation, and both
`--enable-bsd-getopt --enable-db` options. There is no private bootstrap library.
Origin: EmberBSD (AI-assisted). All inherited source licenses remain unchanged.

The fixed initial contract is [bootstrap/libnbcompat.json](bootstrap/libnbcompat.json).
The SDK `ports-libnbcompat-bootstrap` producer configures, builds, and stages
that complete source. Its selected make tuple supplies the shell. Installation
uses the canonical `install-sh -c`, rather than its default move operation.
Every required tool must already belong to the selected initial SDK. Missing
`cp`, `mv`, `ls`, or `diff` is a missing input, not permission for a host fallback.
Configuration also requires the selected native `printf` utility.
The common mksh recipe does not provide a built-in `printf`.

The export applies one infrastructure patch and installs one common shell
diagnostic helper into the source tree. Explicit `EMBERBSD_CONFIGURE_SDK=yes`
requires an absolute selected `EMBERBSD_CONFIGURE_UNAME` executable. The SDK
binds its path, bytes, provenance, and utility alias. System uname paths fail.
Unavailable legacy platform queries return failure without executing a host
tool. Ordinary mode retains its existing platform queries and feature tests.

GCC uses the same helper bytes through its generated new-file patch hunk.
Legacy `GCC_CONFIGURE_SDK` and `GCC_CONFIGURE_UNAME` selectors remain supported.
Conflicting legacy and common selectors fail. Regenerate the GCC hunk with the
selected SDK Python and `generate-configure-diagnostics.py --write`. Its default
mode checks exact byte parity. Do not maintain a separate GCC implementation.
The helper retains GPL-3.0-or-later licensing.

The libnbcompat patch retains the diagnostic routing in `configure` and
`configure.ac`. The latter preserves the canonical `AS_UNAME` body and adds
the same selected helper hook. Both long-long printf probes include `string.h`
to declare `strcmp`. Without this declaration, strict Clang rejects the probes
before they can test `%lld` or `%qd`, incorrectly disabling
`HAVE_WORKING_LONG_LONG`. The tested value and comparison remain unchanged;
no feature result is forced. Exact generated-source delta checks do not
replace a future selected Autoconf regeneration check.

Run `tests/libnbcompat-initial.py` with the selected SDK Python for source checks.
The GCC diagnostic test also checks all 34 patched configure scripts against
the complete canonical release archive. The source/data checks also verify that
both patched probe programs match between Autoconf input and generated configure. Native library and consumer
acceptance remain separate.

For the initial bootstrap, select the same explicit native compiler and ABI
flags used by bootstrap. The optional probe test compiles the original programs
with `-Werror=implicit-function-declaration`, requires their declaration failure,
then compiles and executes both corrected programs against the native libc:

```sh
python3 -B profiles/common-build-tools/tests/libnbcompat-initial.py \
  --cc /absolute/initial-clang \
  --cflag=-isysroot --cflag=/absolute/host-sdk \
  --work-root /absolute/shared-objects/native/tests --analyze \
  --cppcheck /absolute/selected-cppcheck
```

Omit platform-specific `--cflag` arguments when the selected compiler does not
need them. `--analyze` runs that Clang's static analyzer; `--cppcheck` selects
Cppcheck explicitly. A source-only run reports the native probe as skipped.
These tests execute native C programs, not target programs or a full libnbcompat
build. Rebuild a previously configured bootstrap libnbcompat and affected
consumers so the corrected feature result reaches their installed artifacts.
