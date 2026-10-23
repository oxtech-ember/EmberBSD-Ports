# Vala array copy contract

The common profile retains Vala 0.56.19 and its upstream LGPL-2.1-or-later
license. The `valadoc` option defaults to enabled. Disabling that option
removes the documentation generator and its Graphviz dependency. It retains
`valac`, `vapigen`, the compiler library and the upstream `check` target.

## Nullable value arrays

The upstream `objects/property-array.vala` test copies a NULL-terminated
array of nullable structures through a property. The copy helper allocated
only `length` pointer slots. It omitted the final NULL slot. A subsequent
length scan read outside the allocation and could free an invalid pointer.

The array-copy C golden files cover both object-property arrays and generic
arrays. The runtime assertions remain unchanged.

`pkgsrc-vala-array-termination.patch` adds the extra zeroed slot for nullable
value elements in `generate_array_dup_wrapper`. Reference elements retain
their existing behavior. Non-null value elements retain their length-based
allocation. The patch changes the Vala source and its shipped bootstrap C.
It retains the upstream Vala regression and its assertions. Its C golden
file is synchronized with the corrected allocation. No check is suppressed.

The shipped C uses the equivalent nullable predicate without renumbering
the function's generated temporary variables. A pristine Vala 0.56.19 host
compiler reproduces the original distributed C byte for byte. A compiler
built from the compact C patch and a compiler built from fully regenerated
C produce identical C for the unchanged property-array regression.

These are local, AI-assisted adaptations. They have not been submitted or
accepted upstream. The inspected [GNOME main](https://github.com/GNOME/vala/blob/25ede52578acc706c07b8816eeceb914510505b3/codegen/valaccodearraymodule.vala)
and [0.56 branch](https://github.com/GNOME/vala/blob/159ed5597853e78bd983d29df33d23d34bde3830/codegen/valaccodearraymodule.vala)
retain the original guard. The current pkgsrc, FreeBSD, OpenBSD and DragonFly recipes
inspected for this change do not supply this repair.

## D-Bus descriptor exhaustion

The recipe declares `dbus>=1.16.2` in `TEST_DEPENDS`. The normal `test`
phase checks this prerequisite before the upstream `check` target. It does
not add D-Bus to ordinary build or runtime dependencies. Native tests use
the package-owned `dbus-run-session` and `dbus-daemon` from the native prefix.
Cross tests retain the standard target test-dependency role.

Run the focused dependency regression with BSD make and an existing export:

```sh
python3.15 -B profiles/common-build-tools/tests/vala-test-depends.py \
  /absolute/pkgsrc /absolute/new-work --bmake /absolute/bmake
```

The check applies the real Makefile delta to private copies. It evaluates
native and cross roles with the export's dependency and test rules. It
checks test-only selection and rejects missing or tool-scoped declarations.
It does not query a package database, build Vala or execute its tests.

The separate test-only `pkgsrc-vala-dbus-fd-exhaustion.patch` disables
`exit_on_close` on the server's shared session-bus connection. Exhausting
all descriptors can make the transport close before the generated method
handler can duplicate an incoming Unix descriptor. GLib otherwise sends
SIGTERM to a process that has enabled `exit_on_close` on that connection.

The test still exhausts every descriptor slot. Its client still requires
the method request to fail. Its server still requires the client to exit
successfully. It can now observe the expected transport error without a
shared-connection policy terminating the server first. The Vala API is
present in the release's `gio-2.0.vapi`.

A private Unix session bus and a process descriptor limit of 256 reproduce
the original exit status 143 on the host. The single connection-policy
change produces status 0. Both variants use the actual upstream testrunner, including C golden-file
comparison, the real host Vala compiler, GCC16 and GLib 2.90.1.
The expected server C is updated for the added policy call. No system bus service is used.
This behavior is independent of the optional valadoc build.

## Host validation and target boundary

Two isolated host builds use GCC 16.2.0 and GLib 2.90.1. They preserve all
upstream configure checks and build with `--disable-valadoc`. The unchanged
property-array regression fails before the repair with an ASan heap buffer
overflow. It passes after the repair with ASan and UBSan. The compiler built
from fully regenerated C also passes.

A focused invocation uses the chosen host compiler, the matching upstream
VAPI directory and the normal upstream regression:

```sh
"$valac" --vapidir "$source/vapi" --pkg gio-2.0 \
    --enable-checking --disable-version-header --save-temps --cc "$gcc16" \
    -X -g -X -O0 -X -fsanitize=address,undefined \
    -X -fno-omit-frame-pointer "$source/tests/objects/property-array.vala" \
    -o property-array
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ./property-array
```

Cppcheck 2.22.0 checks the actual array module before and after the repair
with GCC-preprocessed host headers and configuration. Both variants have
identical findings: one warning in a GLib header, 39 style findings and two
information records. The header warning is an intentional local ownership
assignment. No new finding is introduced. The analysis retains the normal
value-flow branch limit.

For Cppcheck only, `-Uerrno_t` prevents its standard library model from
rewriting the SDK's real `errno_t` typedef. GCC diagnostic pragmas are
replaced with blank lines in the preprocessed analysis copies because the
Cppcheck parser rejects them. No executable statement or diagnostic category
is removed. GCC 16 `-fanalyzer` also checks the unmodified C translation units
with their real headers and flags. It reports no analyzer finding. Both
variants retain the same GLib atomic qualifier compiler warning.

Apple Clang 21 Static Analyzer also checks the actual C module with the
same host configuration and SDK headers. A deliberate NULL-dereference
control confirms checker operation. Both variants complete with status zero
and the same four `deadcode.DeadStores` findings. They are unused generated
`self` assignments owned by upstream Vala. No checker is suppressed.
Clang runs only in analysis mode and produces no target objects.

Valgrind is unavailable on the Apple Silicon validation host. The ASan/UBSan
runs check invalid memory access and frees. They do not establish leak or
uninitialized-value acceptance. ASan emits a module-map warning in the
failing baseline. Target ABI analysis, cross packaging, installed target
execution and the complete target upstream suite remain separate gates.
