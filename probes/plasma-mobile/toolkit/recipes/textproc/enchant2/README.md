# Enchant 2.8.21

This is the current stable upstream release as checked on 2026-10-13:
<https://github.com/rrthomas/enchant/releases/tag/v2.8.21>.

The recipe derives from pkgsrc fff4deb639a1a640476203c80f752fb77b6cb14b.
Keep the upstream LGPL terms and the pkgsrc SunOS adaptation.
The default provider is current Hunspell with the official en_US dictionary.
UnitTest++ remains a build dependency. The upstream `check` target remains.
No GTK library is required.

A cross build creates target programs. Run the Enchant test executables on
EmberBSD. A successful Mac cross build is not a target runtime test.

For a Mac cross build, set `EMBERBSD_BUILD_GROFF` to a current native
`groff` executable. HTML manuals remain part of the build. Groff 1.24.2
is the current GNU release as checked on 2026-10-13 at
<https://ftp.gnu.org/gnu/groff/>. The native tool selection is AI-assisted
EmberBSD work. It does not replace the target runtime libraries.

The cross build sets `GROFF_BIN_PATH` to the native tool directory.
pkgsrc executes groff through a symlink in `.tools/bin`; its subprocesses
must still resolve to the same native `pre-grohtml`, `post-grohtml`, and
`gsoelim` provider. A direct invocation alone does not test that wrapper path.
