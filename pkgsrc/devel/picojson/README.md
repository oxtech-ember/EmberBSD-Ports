# Common PicoJSON

The recipe uses [upstream commit 111c9be5188f](https://github.com/kazuho/picojson/commit/111c9be5188f7350c2eac9ddaedd8cca3d7bf394), dated 2021-01-17.
This is the current upstream default-branch revision checked for this change.
Archive SHA256: `671f89832a17e9e71398f80c0a326afa2ebe81f4c26d5a9992e1fcd0888ae151`.
The package version is `1.3.0.20210117`; it denotes a snapshot after release 1.3.0.
pkgsrc names the commit archive `picojson-1.3.0.20210117-111c9be5188f7350c2eac9ddaedd8cca3d7bf394.tar.gz`.
Its directory is `picojson-111c9be5188f7350c2eac9ddaedd8cca3d7bf394`.
`../cppcheck/tests/metadata.py` checks that the evaluated distfile has a distinfo record.

The [last release, 1.3.0](https://github.com/kazuho/picojson/releases/tag/v1.3.0), dates from 2015-02-25.
The snapshot includes later upstream fixes for parsing depth, input iteration, integer values and compiler compatibility.
It includes upstream rvalue and mutation APIs. No older header is maintained separately.
The selected header matches Cppcheck 2.22.0 and ZoneMinder 1.38.4 byte for byte.

The package installs the original header, examples, BSD license, pkg-config file and relocatable CMake target `picojson::picojson`.
The CMake interface follows the [FreeBSD Ports integration](https://github.com/freebsd/freebsd-ports/tree/main/devel/picojson).
EmberBSD adds both original upstream tests: normal values and `PICOJSON_USE_INT64`.
Upstream's bundled Picotest files remain test infrastructure and are not installed as a library.
The implementation header and upstream tests are unchanged.

Cppcheck imports the common CMake target. ZoneMinder's JWT consumer selects its existing external-PicoJSON option.
The JWT CMake target spelling and two include paths are corrected for the public header layout.
These consumers must rebuild after a provider update.

The current source gate is `../cppcheck/tests/dependencies.py`.
Source/hash/patch checks do not prove native or target behavior.
Compiler runs, both executable suites, installed consumers, memory and package lifecycle checks remain pending.
The packaging and consumer changes are AI-assisted EmberBSD work.
