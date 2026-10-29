# Groff 1.24.2

Use the current GNU release from <https://ftp.gnu.org/gnu/groff/>.
This version includes the upstream fixes for the HTML preprocessor.
The recipe derives from pkgsrc fff4deb639a1a640476203c80f752fb77b6cb14b.
Keep upstream authorship, GPLv3 terms and the existing pkgsrc adaptations.
The configure patch is rebased to the generated configure script in 1.24.2.

The C23 patch replaces the K&R `matherr` definition with a function prototype.
It preserves the System V exception cases and errno behavior.
This is AI-assisted EmberBSD work. It has not been submitted upstream.

Run the focused regression with a C23 compiler:

```sh
CC=/absolute/clang sh files/check-matherr-c23.sh PATCHED_SOURCE NEW_WORK
```

The fixture compiles the real source with a small System V math API header.
It checks all six error cases and the unknown-case errno contract.
ASan and UBSan check the fixture. The unpatched source fails the C23 compile.
It does not replace tests against a platform's real math header.

The native macOS build passes with its real generated configuration and gnu23.
Cppcheck 2.22.0 finds the same `constParameterPointer` suggestion before and
following the patch. The external System V hook keeps its non-const signature.
Clang Static Analyzer 23.1.3 parses and analyzes the patched fixture without
findings. It rejects the unpatched K&R definition in C23 mode.
Valgrind is not supported on this macOS arm64 host. No Valgrind result is claimed.
The focused test does not allocate memory; macOS LeakSanitizer is unavailable.

The native groff executable renders all three Enchant 2.8.21 manual pages
through `groff -mandoc -Thtml` without Ghostscript. These pages contain no
image pipeline. This does not validate general graphical HTML conversion.
The target groff recipe retains its existing full documentation option and
its Ghostscript dependency. The complete target groff package is not accepted.

## Cross builds

pkgsrc refuses `USE_TOOLS+=TOOL:run` in a cross build, because the build-host
tool cannot run on the target. Installed groff programs do not record the
awk or sed path: only gdiffmk runs `sed` from `PATH`, and NetBSD has both in
its base system. A NetBSD cross build therefore uses them as build tools.
With `groff-docs`, the documentation build runs `gs` on the build host, and
the installed devhtml `DESC` names the image generator that grohtml runs from
`PATH`. The cross build records the name `gs` and depends on the target
Ghostscript package. Native builds keep the upstream runtime tools.

The documentation build also runs the groff it builds (`GROFFBIN`). A cross
build has no proof yet beyond configuration; it may need a native groff.

Check the cross configuration with a configured cross `MAKECONF`:

```sh
MAKECONF=CROSS_MAKECONF python3 profiles/common-build-tools/tests/cross-runtime-tools.py \
    --bmake BMAKE --pkgsrc PKGSRC --makeconf CROSS_MAKECONF
```

The test fails with the upstream `awk:run`, `sed:run`, `gs:run` and `gm4:run`.
It also covers the automake cross dependency on the target m4 package.
