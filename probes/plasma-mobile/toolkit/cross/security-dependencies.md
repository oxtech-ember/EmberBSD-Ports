# Current security dependencies for Plasma

Ports owns the GnuPG and polkit prerequisites for the common Qt 6.12 /
Frameworks 6.31 stack. The [crypto delta](../current-crypto-deps.patch) selects
[GnuPG 2.5.24](https://gnupg.org/download/index.html), the current stable release
checked on 2026-10-12. The [polkit delta](../current-polkit.patch) retains
[polkit 127](https://github.com/polkit-org/polkit/releases/tag/127) and updates
[polkit-qt to 0.201.1](https://download.kde.org/stable/polkit-qt-1/).
Original archives, SHA256 and pkgsrc digests are recorded in the deltas.
These are checksum-verified sources, not a claim of release-signature verification.

## Cross-build corrections

libassuan's configure previously selected the build host's `gpgrt-config`.
Its generated configuration script then leaked the host include/library prefix.
The libgpg-error buildlink now selects the target POSIX shell script and its
metadata. Native builds keep the original selection. `bsd.prefs.mk` must be
loaded before testing `USE_CROSS_COMPILE`; an early unset value loses the fix.

GnuPG 2.5.24 links its g13 tests without `$(LIBINTL)`, although libcommon
calls `gettext`. GNU ld does not use the indirect libintl dependency of
libgpg-error, so the link fails. `patch-g13_Makefile.in` adds the library.
The amd64 result is a build check only; runtime evidence remains AArch64.

polkit uses native GLib generators, g-ir-scanner and g-ir-compiler. Its GIR
queries are cross-compiled and executed on the board through the existing
[common introspection workflow](../../../../profiles/common-graphics/recipes/devel/gobject-introspection/cross.mk).
The query receives only its selected libraries in an isolated directory.
ELF inspection replaces build-host `ldd`; the agent query links both in-tree
polkit libraries. Daemon, PAM helper, tools, GIR and typelibs remain enabled.
polkit-qt's CMake imported pkg-config paths are rooted in the target sysroot.

Reproduce the focused source checks after preparing `plasma-mobile` pkgsrc:

```sh
export BMAKE=/absolute/native/bmake
export MAKECONF=/absolute/cross-mk.conf
export DIGEST=/absolute/native/digest
sh probes/plasma-mobile/toolkit/tests/crypto-deps-source.sh \
    /absolute/distfiles /absolute/pkgsrc "$MAKECONF" /absolute/new-crypto-check
sh probes/plasma-mobile/toolkit/tests/polkit-source.sh \
    /absolute/distfiles /absolute/pkgsrc /absolute/new-polkit-check
```

The checks use original pinned recipes, archive and patch digests, zero-fuzz
patching, exact exported-file comparisons and repeated-patch rejection.
They also exercise real native/cross tool selection without disabling features.
Build the complete packages through normal pkgsrc `package` targets.
Use ordinary alternate-root installation/replacement for the build sysroot.

## CM5 GnuPG evidence, 2026-10-12

GnuPG 2.5.24 and its dependencies were installed on CM5 Rev 1.0, BCM2712D0,
4 GiB RAM, Waveshare CM5-NANO-B. The EmberBSD `EMBERV3DRENDER #1` kernel SHA256
was `6c5aa74d3c33fb6e84ea5c04d6f3df48928deb021cdc908ee972a42df03c7bf5`.
Carrier revision and firmware revision were not re-measured by this check.

`tests/crypto-runtime.sh NEW_OUTPUT` passes against installed libraries:
AES256 symmetric encryption, byte-identical decryption and wrong-passphrase
rejection. It uses synthetic data, a private 0700 GnuPG home, bounded commands
and private agent cleanup. Boot identity is unchanged. It does not access a
user's keyring. The full GnuPG upstream suite, smartcards, key generation,
KWallet integration and long-running service behavior remain unaccepted.

| Object | SHA256 |
| --- | --- |
| GnuPG package | `5480c93e2439eef7314df670efd88c46d5bd2013411c7c93bde1aeee89768b18` |
| libassuan 3.0.2nb1 package | `24b7835e848cfe226c9f2585391ea863b583619eb9e021b0377ec0c3615d43b1` |
| GnuPG CM5 journal | `96fe0ffdf3b73b60fc2b9f781ae548c35bd3ad2cc11e69de63c465c7bb107c16` |
| polkit-qt 0.201.1 package | `7df23c724184d6e4beb42b3c9c871f2e1729ebac4d28820619573678d6399797` |
| polkit 127nb3 package | `136d1deb9233b95e9df787131323f4d25dfc78778ab65e6f135d7765555c7b11` |

polkit's complete package and both real GType queries pass. This does not
validate its authorization decisions, PAM prompts or a live desktop agent.
The source changes here concern build recipes and Meson/CMake metadata, not
cryptographic or authorization algorithms. No new whole-source static-analysis
or Valgrind result is claimed; EmberBSD/AArch64 Memcheck is not validated here.
