# basu native build generator

This recipe retains basu 0.2.1 and all BSD patches from pkgsrc revision
`fff4deb639a1a640476203c80f752fb77b6cb14b`.
Version 0.2.1 remains the latest
[upstream release tag](https://git.sr.ht/~emersion/basu/refs).
EmberBSD recipe changes are AI-assisted. Upstream authorship and licenses remain.

The original recipe applies `REPLACE_PYTHON` to `generate-gperfs.py`.
That selects the target interpreter even though Meson executes this file
on the build host. A cross build then fails with `FileNotFoundError`
when the target interpreter path does not exist on the host.

Use pkgsrc's `REPLACE_TOOL_PYTHON` and `PYTHON_FOR_BUILD_ONLY=tool`.
The shared helper selects `TOOL_PYTHONBIN`. The upstream generator and
its Meson invocation remain unchanged. Python is not a basu runtime dependency.
Meson also receives the declared native gperf 3.3 path. This prevents
selection of an older platform gperf earlier on `PATH`.
The archive uses a unique local filename; its upstream bytes and hashes remain.

Run the regression with an exported pkgsrc tree and the real cross configuration:

```sh
BMAKE=/path/to/native/bin/bmake ruby tests/cross-generator.rb \
    /path/to/pkgsrc /path/to/cross.mk.conf /path/to/basu-0.2.1.tar.gz \
    /path/to/new-result
```

The regression uses the actual pkgsrc interpreter helper on a temporary copy
of the upstream generator. It reproduces the target-interpreter failure,
executes the corrected generator through Meson's capture path, checks the
errno table and prefix handling, runs the selected gperf, and checks failure propagation.
It does not configure, build, or install the package.

The inherited libcap/audit platform settings and BSD source patches remain.
This fix changes no C sources. Complete cross compilation, upstream target
tests, source analysis, installed liboeffis use, and memory checks remain
separate acceptance gates.

## Error-map section retention

The real upstream `test-bus-marshal` fails to link with GCC16/LLD23.
Its `__start_BUS_ERROR_MAP` and `__stop_BUS_ERROR_MAP` references become undefined.
The upstream header already uses `retain`, but the NetBSD-target object lacks
`SHF_GNU_RETAIN`. The compiler's `used` attribute alone cannot retain a section
against linker garbage collection. The inherited header suppresses attribute warnings.

The Meson patch selects the supported `-z nostart-stop-gc` behavior on NetBSD.
It retains registered error maps when their boundary symbols are referenced.
`--gc-sections` stays enabled for unrelated code and data.
This follows the [LLD section-registration contract](https://lld.llvm.org/ELF/start-stop-gc.html).
No C source or test is removed. No undefined-symbol diagnostic is disabled.

Run the causal check against a configured production build with compiled tests:

```sh
NINJA=/absolute/native/ninja CC=/absolute/pkgsrc-wrapper/aarch64--netbsd-gcc \
CWRAPPERS_CONFIG_DIR=/absolute/work/.cwrapper/config \
READELF=/absolute/cross/aarch64--netbsd-readelf \
    ruby tests/error-map-link.rb /absolute/basu/output /absolute/new-results
```

The check reads the actual upstream link command from Ninja.
The original command must fail on the missing map boundary.
The corrected command must link and define both boundaries and the map table.
This is target-ELF link evidence, not execution of the marshal test.

## POSIX error-string handling

The nb2 patch checks the POSIX `strerror_r` result before reading its string.
A failed conversion leaves the existing error message and ownership unchanged.
The existing ERANGE retry remains intact. The shared buildlink requires nb2.

The regression extracts the two actual functions from the selected source tree.
It uses the real allocation helpers and controls only the external libc result.
Ten repaired cases cover constant and owned messages, conversion failure,
ERANGE retry, a full buffer, success, and the native libc conversion.
The macOS Clang 23.1.3 run passes ASan, UBSan, and enabled leak checks.
This bounded native result does not establish target daemon or full-library behavior.

```sh
CC=/absolute/clang ruby tests/strerror.rb \
    /absolute/upstream-basu /absolute/patched-basu /absolute/new-results
```

Source analysis used actual AArch64 compile arguments and target headers for
`bus-error.c`, `bus-socket.c`, and `socket-util.c`.
GCC 16.2 reports the NULL argument before the fix and no longer reports it after.
Its inherited allocation-attribute warning and complex-path limits remain.
Clang 23.1.3 accepts the repaired error unit without a finding.
The adapted socket helper has one inherited dead-store finding at its descriptor reset.
The unadapted Linux socket units cannot compile with the BSD target headers;
that portion does not have a comparable successful baseline.
Cppcheck 2.22 cannot parse the full ELF-map/GNU declarations in this configuration.
These are explicit coverage limits, not a clean full-library audit.
Ports owns the remaining analysis gaps and inherited diagnostics.
Valgrind Memcheck was not run on macOS/AArch64 or EmberBSD/AArch64.
