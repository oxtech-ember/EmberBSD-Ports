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

`pkgsrc-vala-array-termination.patch` adds the extra zeroed slot for nullable
value elements in `generate_array_dup_wrapper`. Reference elements retain
their existing behavior. Non-null value elements retain their length-based
allocation. The patch changes the Vala source and its shipped bootstrap C.
It does not change the existing upstream regression or suppress a check.

The shipped C uses the equivalent nullable predicate without renumbering
the function's generated temporary variables. A pristine Vala 0.56.19 host
compiler reproduces the original distributed C byte for byte. A compiler
built from the compact C patch and a compiler built from fully regenerated
C produce identical C for the unchanged property-array regression.

These are local, AI-assisted adaptations. They have not been submitted or
accepted upstream. The inspected GNOME main and 0.56 branches retain the
original guard. The current pkgsrc, FreeBSD, OpenBSD and DragonFly recipes
inspected for this change do not supply this repair.

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

Valgrind is unavailable on the Apple Silicon validation host. The ASan/UBSan
runs check invalid memory access and frees. They do not establish leak or
uninitialized-value acceptance. ASan emits a module-map warning in the
failing baseline. Target ABI analysis, cross packaging, installed target
execution and the complete target upstream suite remain separate gates.
