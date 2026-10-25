# Common SimpleCpp 1.9.1

The source is the [upstream 1.9.1 release](https://github.com/cppcheck-opensource/simplecpp/releases/tag/1.9.1).
Tag commit: `2499b51390e6ea74b8fbad91154f5529134de31a`, released 2026-08-25.
Archive SHA256: `d26e36a8a6462d1655e03d67a95f5cd0228bffb1873c9349b971093494a0df59`.
The next upstream commit changes CI only. No implementation changes follow this release.

The common recipe adds installation to upstream CMake.
It preserves the CLI and complete CMake unit-test executable.
Both link the installed-library target instead of separate implementation objects.
The public header and implementation match Cppcheck 2.22.0 byte for byte.
The library exports `simplecpp::simplecpp` and the upstream Windows import/export definitions.
Its ABI series is `1.9`; the CMake version contract requires an exact release.
Review ABI and rebuild consumers before changing this version.
Cppcheck is the only SimpleCpp library consumer found in the Ports recipes.
Chocolate Doom's `man/simplecpp` is an unrelated Python documentation script.

The upstream license remains BSD Zero Clause and is installed with the package.
The packaging patch is AI-assisted EmberBSD work.
The current source gate is `../cppcheck/tests/dependencies.py`.
It checks exact archive hashes, patch replay, consumer source identity and package interfaces.

Native and target compilation, installed CLI/library consumers, memory checks and package lifecycle remain pending.
The ordinary `test` target retains the complete upstream CMake unit suite.
Upstream also provides pytest integration and GCC/Clang comparison suites.
Those files remain unchanged; they need separate tool admission and are not reported as executed.
