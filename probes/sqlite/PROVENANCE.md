# SQLite source provenance

- Upstream: [SQLite](https://www.sqlite.org/).
- Selected release: **3.54.1**, released **2026-10-16**.
- Official [download metadata](https://www.sqlite.org/download.html) and
  [change log](https://www.sqlite.org/changes.html) were checked on 2026-10-22.
- Source ID: `2026-10-16 14:45:20 555e07ef33f69a0957d24d8e555b702464a131d6f1607f4c3c1e4551e8e6ca76`.
- Archive: `https://www.sqlite.org/2026/sqlite-autoconf-3540100.tar.gz`.
- Size: **3,332,984 bytes**.
- SHA256: `926ef8d3eab93fbf6e06011901273eec076b25594a4e1cdadd50c987f4f6d64e`.
- Official archive SHA3-256:
  `b6ced585c750916b1052667239a12c25a7ff34e7f06e1e6e01ecb0427657d9c4`.
- SQLite deliverables are [public domain](https://www.sqlite.org/copyright.html).
  Original dedications remain in the sources and installed headers. The package
  preserves a dedication excerpt and the build-only Autosetup BSD-style license.
- The inherited pkgsrc patch disables automatic Darwin rpath selection.
  Core SQLite C sources are unchanged. The selected shared-library ABI remains
  `libsqlite3.so.0`, with the upstream versioned installation name.
- Packaging, builders and C/CMake contracts are EmberBSD contributions,
  AI-assisted and MIT licensed. No upstream acceptance is claimed.

The [common package recipe](../../profiles/common-build-tools/recipes/databases/sqlite3) owns the current
library. It retains the useful common pkgsrc feature policy and replaces the
older provider at the same prefix. The standalone helper reads its features
from the canonical recipe. The native private prefix exists for checks with
the same source, GCC16 and features; it is not an older application runtime.

Native and target builds use GNU C17. The cross compiler and sysroot retain
AArch64 EmberBSD provenance. Autosetup's accepted canonical host spelling adds
an explicit vendor field; it does not replace any target OS component.

The installed dynamic CLI exposed a missing runtime path when only
configure-time LDFLAGS were supplied. Its exact source-ID check rejected a
system SQLite implementation. Passing LDFLAGS to make, as required by the
upstream dynamic-shell rule, fixes the selected-prefix linkage. This changes
packaging flags and leaves SQLite source unchanged.
