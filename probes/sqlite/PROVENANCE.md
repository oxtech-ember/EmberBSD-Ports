# SQLite source provenance

- Upstream: [SQLite](https://www.sqlite.org/).
- Selected release: **3.54.0**, released **2026-10-09**.
- Official [download metadata](https://www.sqlite.org/download.html) and
  [change log](https://www.sqlite.org/changes.html) were checked on 2026-10-15.
- Source ID: `2026-10-09 15:46:58 be8d059e9a49089ab2dce5ed26dd87aaf598fdc5fbe0b107c0dd758464bcd5e3`.
- Archive: `https://www.sqlite.org/2026/sqlite-autoconf-3540000.tar.gz`.
- Size: **3,332,512 bytes**.
- SHA256: `134ec0802dda5795816e25d25872d20b312cb3973438c49b30bc40b7705ea9ed`.
- Official archive SHA3-256:
  `f5e3e724e9c9b3b5d512c76b02082091a59eeea9becd169a9fbf4d376403acce`.
- SQLite deliverables are [public domain](https://www.sqlite.org/copyright.html).
  Original dedications remain in the sources and installed headers. The package
  preserves a dedication excerpt and the build-only Autosetup BSD-style license.
- No SQLite source patch. The selected shared-library ABI remains
  `libsqlite3.so.0`, with the upstream versioned installation name.
- Packaging, builders and C/CMake contracts are EmberBSD contributions,
  AI-assisted and MIT licensed. No upstream acceptance is claimed.

The [common package recipe](../../pkgsrc/local-robotics/sqlite3) owns the current
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
