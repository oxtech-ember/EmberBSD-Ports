# Actual KiCad API contract

This harness builds the actual KiCad 10.0.7 `api/CMakeLists.txt` and all
15 schemas. It links a separate consumer through the public `kiapi` target.
It checks `major()`, `minor()` and `patch()` accessors, exact protobuf bytes
`08 0a 18 07`, and the unchanged descriptor and JSON field names. It does
not exercise the IPC transport or the JSON conversion API.

Use the complete source from [prepare-source.sh](../../prepare-source.sh),
the common GCC 16.2.0 compiler, and installed protobuf 36.2. Native `protoc`
and target libraries must use the same release and source patches. Record
its SHA256 before configuration; the harness also checks its actual exit
status and exact `libprotoc 36.2` version. The target SDK generator is not
executed. Config-mode discovery requests the full C++ version `36.2.0`.

For a cross build, pass the coherent EmberBSD toolchain and sysroot:

```sh
cmake -S /path/to/tests/api -B /path/to/new-api-build -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=/path/to/aarch64.cmake \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DKICAD_SOURCE=/path/to/prepared-kicad \
  -DProtobuf_DIR=/path/to/sysroot/usr/pkg/lib/cmake/protobuf \
  -DProtobuf_PROTOC_EXECUTABLE=/path/to/native/bin/protoc
cmake --build /path/to/new-api-build --target kiapi-version-contract --parallel 1
```

The toolchain must keep target library, include and package searches inside
the sysroot and program searches on the host. Transfer only the contract
and its `libkiapi` runtime to the target. Use installed common protobuf,
Abseil, zlib and GCC16 runtime packages. Keep the private `libkiapi` directory
in a controlled loader path; do not transfer the SDK or generator.

For a native check, omit the cross toolchain, select native GCC16 explicitly,
and select the matching installed native dependency prefix. Run:

```sh
/path/to/native-api-build/kiapi-version-contract
valgrind --tool=memcheck --track-origins=yes --leak-check=full \
  --show-leak-kinds=all --errors-for-leak-kinds=all --error-exitcode=99 \
  /path/to/native-api-build/kiapi-version-contract
```

The NetBSD baseline fails during compilation because `sys/types.h` exposes
function-like `major` and `minor` macros. The patch preincludes that real
header and removes only those names in the `kiapi` target and its CMake
consumers. The target's `PUBLIC` option keeps the library and consumer
consistent. It does not rename fields or change `protoc` globally.

GCC16 AArch64 and native builds pass. All 30 generated files are byte-identical
to the baseline. The native contract passes strict Memcheck with zero errors,
zero live blocks and no suppressions. Clang 19 analysis reproduces the target
baseline macro errors and reports no findings for the repaired generated
translation unit or native/target consumer. Cppcheck 2.22 is incomplete:
actual dependency headers use qualified feature predicates that its parser
cannot evaluate. GCC16-measured analysis copies of Abseil's attribute
predicates expose the next parser failure in protobuf `port_def.inc` at its
qualified `always_inline` predicate. No Cppcheck-clean result is claimed.

The same AArch64 contract passes in the EmberBSD VM with ordinary installed
protobuf, Abseil and zlib packages. Its executable, private `libkiapi` and all
loaded providers match their recorded hashes. This is an API source probe.
The full application build, other consumers' use of device macros, installed
IPC behavior and GUI workflows need separate acceptance.
