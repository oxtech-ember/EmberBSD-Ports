# Little CMS compatibility tests

These checks exercise the common library selected by the package recipe. The
PDFium backports originate from revision `fa4d5f8fbd89ea07273529daf9fd24fe1c7f6b9a`;
the individual patch headers identify the donor files. `0027` retains only
the TRC-to-colorant tag-link guard. The library retains its own allocator;
PDFium's allocator policy belongs to its consumer context.

Run these tests explicitly after applying the complete package patch series.
Choose the native compiler, the patched source directory, and its built dynamic
library explicitly. The following example is for a Darwin host; on ELF hosts
replace `-Wl,-dead_strip` with `-Wl,--gc-sections`.

```sh
LCMS_CC=/path/to/native-prefix/bin/clang
LCMS_SRC=/path/to/patched/lcms2-2.19.1
LCMS_LIB=/path/to/selected/liblcms2.dylib
LCMS_TESTS=/path/to/pkgsrc/graphics/lcms2/files/tests
LCMS_OUT=/path/to/temporary/output
mkdir -p "$LCMS_OUT"
for test in color-transform lcms-float-grid lcms-grid-overflow tag-link; do
    "$LCMS_CC" -I"$LCMS_SRC/include" "$LCMS_TESTS/$test.c" "$LCMS_LIB" -lm -o "$LCMS_OUT/$test"
    "$LCMS_OUT/$test" || exit 1
done
"$LCMS_CC" -I"$LCMS_SRC/include" -I"$LCMS_SRC/src" "$LCMS_TESTS/lcms-fast-floor.c" -lm -o "$LCMS_OUT/floor"
"$LCMS_OUT/floor"
"$LCMS_CC" -O0 -ffunction-sections -fdata-sections -I"$LCMS_SRC/include" -I"$LCMS_SRC/src" "$LCMS_TESTS/lcms-matrix-overflow.c" -Wl,-dead_strip -o "$LCMS_OUT/matrix"
"$LCMS_OUT/matrix"
```

The float-grid test uses the public two-dimensional CLUT API, while the floor
and matrix checks exercise the library's actual internal evaluators. The grid
overflow test covers wrapped allocation sizes, and the tag test checks both a
valid tone-curve link and an invalid tone-curve-to-colorant link. To check a
cross target, compile the same sources with the selected target compiler,
explicit target and sysroot, and `-fsyntax-only`; executing those binaries
requires a compatible target runtime.
