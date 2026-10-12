# Current libsecret with complete cross-build metadata

libsecret 0.21.8.2 is the current stable release in the
[official GNOME archive](https://download.gnome.org/sources/libsecret/0.21/).
The complete package cross-builds from macOS with GCC 16.2 for EmberBSD AArch64.
It retains Secret GIR/typelib, Vala bindings, translated messages, `secret-tool`,
manual pages and reference documentation. Both real library and mock-service
GType queries execute on the target through the common verified transport.

## Native generators

Use native Vala 0.56.19 (`valac`, `vapigen`) and gi-docgen 2026.1. They generate
C, VAPI and documentation on the build host; target libraries and GLib metadata
come from the common EmberBSD sysroot. Native package builds retain the usual
pkgsrc tool dependencies. Missing selected native prefixes fail configuration.

The optional helper builds the original [gi-docgen archive](https://pypi.org/project/gi-docgen/2026.1/)
with the existing host Python. Upstream gi-docgen requires Python; the helper
adds no Python source. Install its native `build`, `installer`, `setuptools`,
Markdown, MarkupSafe, Pygments, Jinja2, packaging and typogrify dependencies.
For Python older than 3.11, upstream also requires tomli.
Provide native Graphviz `dot`; the helper checks actual SVG generation.

```sh
sh build-gi-docgen-host.sh /absolute/distfiles /absolute/native-python \
    /absolute/dot /absolute/new-work
```

The helper verifies the archive SHA256 before extraction. It builds without
isolated dependency downloads, records native tool hashes and wraps the
installed entry point with its private module path. This private build helper
is not a second target runtime provider. Set these private MAKECONF inputs:

```make
EMBERBSD_GI_DOCGEN_HOST=/absolute/new-work/prefix
EMBERBSD_VALA_HOST=/absolute/native-vala-prefix
```

The common GI transport inputs are also required. `libsecret-tools.sh` queries
the actual native/cross recipes and checks absent-generator refusals:

```sh
BMAKE=/absolute/bmake sh ../tests/libsecret-tools.sh \
    /absolute/prepared-pkgsrc /absolute/cross.mk /absolute/new-check
```

## Native peer credentials

The upstream BSD ancillary-credential path calls an undefined `set_local_creds`
and references an undeclared `fd`. Its fixed-size buffer also cannot hold an
arbitrary supplementary-group array. The EmberBSD patch uses the existing
`SOL_LOCAL`/`LOCAL_PEEREID` socket option on the NetBSD-compatible ABI.
It reads the kernel-recorded peer PID and effective UID without enabling
ancillary credential delivery. Other platform branches remain unchanged.

```sh
sh ../tests/libsecret-credentials/build.sh /absolute/cross-tools \
    /absolute/sysroot /absolute/configured-libsecret-source \
    /absolute/libsecret-0.21.8.2.tar.xz /absolute/new-check
```

The original source fails GCC16 compilation with both reported defects.
The fixed actual source cross-links with warnings treated as errors except
upstream's unrelated unused parameters. Run the resulting `credentials`
on EmberBSD: 32 real socket-pair cycles check PID/effective UID, disabled
ancillary delivery, invalid markers, closed peers and an invalid descriptor.
The original-source control and the target regression passed on CM5.

Cppcheck 2.22 on the actual target-preprocessed fixed source and Clang Static
Analyzer against the target headers reported no diagnostics. Valgrind was not
run because a supported runner is unavailable for this target. These bounded
checks do not prove whole-library memory safety or secret-service correctness.

## Acceptance boundary

On 2026-10-12 the complete package passed normal dependency, manifest,
interpreter, permission, PIE, RELRO, RPATH and build-path checks. Installation
into the common sysroot and normal package installation on CM5 passed.
The target package verifier checked 413 files. The package SHA256 is
`10672a3456cd11b07c287926814252d9e2c80b2a89c2ccfcfe591dfb520b063a`.

Seven unmodified upstream suites also passed on the installed CM5 package:
`test-hex`, `test-secmem`, `test-dh`, `test-dh-length`, `test-hkdf`,
`test-attributes` and `test-value`. Copy the executables from the configured
`output/egg` and `output/libsecret` directories, verify their SHA256, then run
each on the target with core dumps disabled. The other upstream suites require
a mock Secret Service and were not run in this bounded check.

A running Secret Service, KWallet integration, interactive password prompts
and the complete accelerated Plasma session remain unaccepted.
