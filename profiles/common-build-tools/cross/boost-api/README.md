# Installed Boost API consumer

This consumer uses the normal installed Boost 1.92.0 headers and shared
libraries. It finds their installed CMake packages. Boost.System is header
only. The binary links Boost.Locale, Filesystem, Thread and Unit Test Framework.
Locale tests select the ICU backend explicitly.

The five cases check exact errno values, UTF conversion and rejection,
filesystem contents and error paths, a thread/future sum of 500500, and ICU
casing, normalization, encoding, collation and number formatting. The runner
repeats all cases four times. A separate real Boost.Test failure must return
201. Each cycle records the libraries loaded by the target process.

## Prepare

Select CPython 3.15 and SDK host API 1. Use clean Ports and SDK checkouts.
First install the normal headers, libraries, ICU runtime/SDK and GCC16 runtime
packages into the build-host sysroot. The archive directory must contain the
exact packages registered there. The helper does not install packages.

```sh
python3.15 -B profiles/common-build-tools/cross/boost-api/prepare.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --sysroot /absolute/sysroot --cross-tools /absolute/cross-prefix \
    --cmake /absolute/cmake/bin/cmake --packages /absolute/packages/All \
    --work /absolute/new-consumer-work
```

The helper compares installed catalogs, payload hashes, modes and links with
the real package archives. It records source revisions and compiler identities.
It builds with GCC 16.2.0, warnings as errors and UBSan traps. It records the
ELF runtime closure and requires the common `libstdc++.so.7` provider. It uses
the shared [loaded-library helper](../../../common-graphics/cross/gui-cad-api/loaded.h).
It copies no target libraries and sets no runtime loader override.

Install the same normal runtime packages on EmberBSD. Copy and extract the
generated `boost-api.tar.gz`. Run its target script with a new absolute log path:

```sh
sh /absolute/bundle/run.sh /absolute/bundle /absolute/new-target-logs
```

The runner verifies bundle and runtime hashes. Every loaded library must match
the recorded closure. It requires the four Boost libraries, common C++ runtime
and exactly one GCC unwind runtime. This is a focused installed API test; it
does not replace the full upstream Boost test suite or establish KiCad acceptance.

An actual GCC16 AArch64 configure and build through these installed imported
targets passes. The helper verifies the complete selected package payloads
and records 18 runtime providers. The runtime search path is
`/usr/pkg/gcc16/lib:/usr/pkg/lib`. Target execution remains a separate gate.

## Native companion and analysis

The optional native companion runs the first two header-only cases. It embeds
upstream Boost.Test headers and builds no native Boost library. It does not
qualify the target locale, filesystem or thread implementations.

```sh
cmake -S profiles/common-build-tools/cross/boost-api -B /absolute/new-native \
    -DCMAKE_CXX_COMPILER=/absolute/native-gcc16/bin/g++ \
    -DEMBER_BOOST_NATIVE_HEADERS=ON \
    -DEMBER_BOOST_INCLUDE=/absolute/sysroot/usr/pkg/include
cmake --build /absolute/new-native --parallel 1
valgrind --leak-check=full --show-leak-kinds=all --errors-for-leak-kinds=all \
    --error-exitcode=99 /absolute/new-native/boost-api --report_level=detailed
```

The GCC16 native companion passes eight assertions and strict Memcheck with
zero errors and zero live blocks. The full target translation unit passes GCC16
compilation and Clang static analysis. Clang is used only for analysis.
Cppcheck 2.22.0 cannot parse this target's NetBSD `__END_DECLS` expansion or
the native GCC16 header attributes in the actual preprocessed translation
units. These parser failures remain explicit; they are not clean analysis
results. UBSan traps cover the consumer, not the prebuilt Boost libraries.
