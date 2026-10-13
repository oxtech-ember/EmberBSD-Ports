# Activities version-header regression

The daemon has two independent version values.
ECM generates the package version `KACTIVITYMANAGERD_VERSION_STRING` as `6.7.5`.
`src/service/Version.h` defines the D-Bus protocol version as `7.0.0`.
The local protocol header can shadow the generated `version.h` on a case-insensitive host.
The first affected translation unit is the real `src/service/Application.cpp`.
The installed PlasmaActivities version header is not the cause.

The recipe names the generated header `kactivitymanagerd_version.h`.
The application includes that header and retains the original protocol header.
The fix changes neither the package version nor the protocol version.

Use an extracted, verified upstream archive and a configured target build:

```sh
ruby tests/activitymanager-version.rb \
    /absolute/kactivitymanagerd-6.7.5 \
    /absolute/configured-build \
    /absolute/new-results
```

The test reads the actual target compilation database.
It applies both recipe patches to private source copies.
It retains the compiler, target headers, macros and compile options.
It copies the real protocol header under the conflicting lowercase name.
This makes the negative control reproducible on case-sensitive hosts too.
The original application must fail on the missing package-version macro.
The patched application must pass `-fsyntax-only` with both headers present.
The test also checks that CMake uses the same unique generated name.
It retains the original protocol header bytes.

For pkgsrc cwrappers, the test copies the existing wrapper configuration.
It maps only its private result directory and redirects its own wrapper log.
It does not edit the build source, dependency tree or installed headers.
Set `CWRAPPERS_CONFIG_DIR` if the wrapper configuration is not adjacent to its binary directory.
The results include complete commands and a compilation database for the patched unit.

The macOS/GCC16 cross regression passes with the configured EmberBSD AArch64 headers.
This is a compile regression, not an installed daemon or desktop runtime check.
Full package checks and target D-Bus activation remain separate requirements.

## Source-analysis boundary

Clang Static Analyzer 23.1.3 completes the upstream and patched application unit without findings.
The comparison uses the configured target flags, EmberBSD headers and generated MOC headers.
The upstream analysis pre-includes the real generated package header to pass the known include error.
The daemon code and protocol header stay unchanged in that comparison.

Cppcheck 2.22.0 stops identically for both units in QtCore `qtypes.h`.
Its preprocessor cannot determine `SIZE_MAX`, even with the target GCC16 predefined macros and default include paths.
This is an analysis limitation, not a clean Cppcheck result.
No diagnostic category is suppressed.
No Valgrind result is claimed for this compile-only regression.
The executable daemon requires separate memory and runtime checks on a supported target.
