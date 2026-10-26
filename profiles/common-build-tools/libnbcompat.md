# Complete initial libnbcompat

The common recipe remains `pkgtools/libnbcompat`, version 20251029, revision 1.
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

The libnbcompat patch changes only the recipe revision and diagnostic routing
in `configure` and `configure.ac`. The latter preserves the canonical `AS_UNAME`
body and adds the same selected helper hook. Exact generated-source delta checks
do not replace a future selected Autoconf regeneration check.

Run `tests/libnbcompat-initial.py` with the selected SDK Python for source checks.
The GCC diagnostic test also checks all 34 patched configure scripts against
the complete canonical release archive. These are source/data checks; native
library, C analysis, memory, and consumer acceptance remain separate.
