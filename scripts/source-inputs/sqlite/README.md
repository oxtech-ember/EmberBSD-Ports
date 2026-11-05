# Common SQLite source and Chromium recovery amalgamation

`source.py` prepares the official full source archive using the common
`databases/sqlite3` version, checksums and complete patch set. It requires an
SDK source checkout with `sourceprep.ZIP_ARCHIVE_API = 1` and verifies the
source receipt before reuse. Run `source.py --sdk-source "$SDK_SOURCE" --help`
for the common prepare and verify commands.

`generate-chromium.py` consumes that prepared tree and the selected Chromium
`third_party/sqlite` directory. It uses the selected native compiler, make,
Tcl 9.1 and ICU from the host prefix. Its output is content-addressed and
contains SQLite's production recovery amalgamation as `sqlite3.c` and
`sqlite3.h`, the upstream-generated `rename_exports.h`, and `shell/shell.c`.
The `dev/` directory contains the corresponding developer configuration. Configuration uses
Chromium's common, production and developer flag lists, including its privacy and
recovery policy; it does not use the bundled SQLite source.

```sh
"$HOST_PREFIX/bin/python3.15" -B generate-chromium.py \
  --sdk-source "$SDK_SOURCE" --source "$SQLITE_SOURCE" \
  --chromium "$CHROMIUM_SOURCE/third_party/sqlite" --work "$SQLITE_WORK" \
  --host-prefix "$HOST_PREFIX" --tcl "$HOST_PREFIX/bin/tclsh9.1" \
  --git "$GIT" --lock-root "$LOCK_ROOT" --jobs "$JOBS"
```

Use explicit `--host-cflag` and `--host-ldflag` for selected host ABI inputs
when required. The lock directory must exist. Source validation may also need
`--archive`, `--patch`, `--pkgsrc-export` and `--export-patch` as described by
`source.py`. The generated output is an input to a consumer, not an installed
package or proof of a target application build.

The Electron producer selects the generated output explicitly using
`--sqlite-source`, `--sqlite-archive`, and `--sqlite-amalgamation`, together
with its selected `--sqlite-patch` and optional `--sqlite-pkgsrc-export` and
`--sqlite-export-patch`. It verifies the common
source receipt, Chromium policy and extractor, generated file hashes, and generated file hashes. It does not require an installed SQLite library. The selected source view
projects both amalgamations and the common source test directory; the rest of
Chromium's SQLite wrapper is unchanged. Reconfiguration accepts a completed verified projection
after an interrupted GN run and rejects a foreign or mixed projection.
