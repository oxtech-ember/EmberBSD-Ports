# Common header-only C++ providers

These versionless package roots provide shared C++ headers and their CMake
package metadata:

- `devel/argparse` (3.2)
- `devel/dynamic_bitset` (1.3.3), using the shared `devel/libpopcnt` provider
- `devel/libpopcnt` (4.2)
- `devel/magic_enum` (0.9.8)
- `devel/thread-pool` (5.1.0)

Consumers use the Ports package and its exported include/CMake interfaces.
They do not vendor another copy or download these dependencies during their
own build. The normal exporter adds these common `pkgsrc/` overlay recipes to
the package catalog. `pkgsrc/replaces` applies only when an overlay replaces an
existing upstream recipe.

The shared test consumer at
[`tests/cpp-header-providers`](../tests/cpp-header-providers/CMakeLists.txt)
resolves and links all five installed CMake targets. It also checks the
transitive `Threads::Threads` interface and exercises the public headers. A
host run checks these portable headers and exported CMake metadata; it does not
claim AArch64 execution or full application acceptance.
