# libdrm GCC16 diagnostics

The libdrm 2.4.134nb4 recipe preserves its strict warning policy after the
first `bsd.prefs.mk` include. MAKECONF selects base compiler flags there.
Adding the recipe flags before that include lost `-Wno-error=cpp` when the
common development and toolkit profiles assigned `CFLAGS=-O2`.

The imported i915 header retains all four packed context-engine records.
GCC16 reports that their packing attributes are unnecessary on amd64. Scoped
GCC diagnostic push/warning/pop directives keep those warnings visible without
changing the records. The surrounding compilation still uses `-Werror` and
`-Wpacked`. A separate packed record outside those scopes remains an error.
The existing USB and Faux-bus `#warning` diagnostics remain visible. Their
unsupported operations still return an error; this patch adds no bus support.

Run the focused regression with an actual configured amd64 libdrm work tree:

```sh
BMAKE=/absolute/native-prefix/bin/bmake \
    ruby profiles/common-graphics/tests/libdrm-gcc16-diagnostics.rb \
    /absolute/exported-pkgsrc /absolute/cross-mk.conf \
    /absolute/configured-libdrm-source /absolute/new-check
```

The regression creates a private recipe/profile overlay and source copy.
It replays four real post-wrapper GCC16 invocations with private outputs.
It checks fifteen independent size, alignment and offset expectations.
It also checks the restored warning policy and an unrelated fatal packing
warning. Native ASan/UBSan execution covers an unaligned packed field access.
It does not execute target objects or test a DRM device.

The initial amd64 source check compiled `intel_bufmgr.c`,
`intel_bufmgr_fake.c`, `intel_bufmgr_gem.c` and `xf86drm.c`. Cppcheck 2.22.0
reported the same 152 findings before and after this diagnostic-only patch.
These include an inherited possible null dereference in `intel_bufmgr_fake.c`.
GCC16 `-fanalyzer` likewise retained three allocation/null-dereference findings
at lines 553, 576 and 1599 of that file. The comparison retained warning
categories but removed general `-Werror` in both analyzer inputs so baseline
diagnostics could not stop path analysis. No new findings were introduced.
These inherited findings remain unresolved in the Ports libdrm owner scope.
This is not a clean static-analysis result.

ASan/UBSan passed the host boundary check. LeakSanitizer is unsupported on this
macOS host; the fixture allocates no dynamic memory. Valgrind was not run.
Full package build, staging and installed runtime/device acceptance remain
separate gates. Historical AArch64 results keep their recorded package scope.
