# Groff 1.25.0

The recipe uses the GNU 1.25.0 release. The configure patch selects the
`g` prefix for commands that can conflict with the system roff tools.
The recipe installs the corresponding GNU command names under
`${PKGGNUDIR}bin`. Upstream removed the System V `matherr.c` source in
this release.

The `perl:run` tool provides Perl for installed programs. A cross build
runs host Perl. The pkgsrc cross tools set installed scripts to target Perl.

The macOS tools locate their font files, macro packages, and helper
programs relative to the installed executable.

## Cross builds

pkgsrc refuses `USE_TOOLS+=TOOL:run` in a cross build, because the build-host
tool cannot run on the target. Installed groff programs do not record the
awk or sed path: only gdiffmk runs `sed` from `PATH`, and NetBSD has both in
its base system. A NetBSD cross build therefore uses them as build tools.
With `groff-docs`, the documentation build runs `gs` on the build host, and
the installed devhtml `DESC` names the image generator that grohtml runs from
`PATH`. The cross build records the name `gs` and depends on the target
Ghostscript package. Native builds keep the upstream runtime tools.

The native tools profile selects `-groff-docs -x11` for native groff. Ports
use the native groff to format manual pages, which needs neither option. This
keeps Ghostscript, netpbm, CUPS, mDNSResponder and native X11 libraries out of
native tool closures. The target recipe keeps both default options.

The documentation build also runs the groff it builds (`GROFFBIN`). A cross
build has no proof yet beyond configuration; it may need a native groff.

Check the cross configuration with a configured cross `MAKECONF`:

```sh
MAKECONF=CROSS_MAKECONF python3 profiles/common-build-tools/tests/cross-runtime-tools.py \
    --bmake BMAKE --pkgsrc PKGSRC --makeconf CROSS_MAKECONF
```

The test fails with the upstream `awk:run`, `sed:run`, `gs:run` and `gm4:run`.
It also checks the native and target groff options separately.
It also covers the automake cross dependency on the target m4 package.
