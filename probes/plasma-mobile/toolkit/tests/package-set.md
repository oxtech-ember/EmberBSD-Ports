# Runtime package-set audit

`cross/prepare-package-set.rb` prepares an offline EmberBSD package set for
the current AArch64 sysroot. Its target metadata uses the retained NetBSD
11.0 ABI identifiers. The caller supplies exact installed root package names.
Native `pkg_info -K ... -e ...` resolves their actual `@pkgdep` constraints.
The output order places each dependency before its consumer.

The archive index contains one absolute `.tgz` path per line. The output must
not exist. Use native Ruby and bsdtar with libarchive support.

```sh
PKG_INFO=/absolute/native/pkg_info BSDTAR=/absolute/native/bsdtar \
    ruby probes/plasma-mobile/toolkit/cross/prepare-package-set.rb \
    /absolute/sysroot/usr/pkg/pkgdb /absolute/archive-paths.txt \
    /absolute/new-package-set plasma6-plasma-desktop-6.7.5nb4
```

Select the root name from the actual installed database. The example version
is illustrative. The command performs these checks before publishing output:

- Resolve every dependency to exactly one installed package. Reject cycles.
- Match each archive's `+CONTENTS` with the installed manifest.
- Check the archive's `OPSYS`, `OS_VERSION`, `MACHINE_ARCH` and `OBJECT_FMT`.
- Match every declared metadata file with the installed copy.
- Stream every regular file through MD5 and compare it with the pkgtools
  manifest. Match symbolic link targets. Resolve hard links to verified data.
- Reject missing, duplicate and unlisted payload members or invalid paths.
- Copy the selected archive and verify its SHA256 against the source digest.
- Confirm that installed metadata did not change during the audit.

A rejected candidate does not hide a later valid archive with the same name.
The auditor copies into a private temporary directory beside the output.
It renames that directory only after all packages pass. Normal errors and
interrupts remove that temporary directory. An existing output is preserved.
Forced process termination or power loss can leave a hidden temporary directory;
it is never an accepted package set.

The result contains `packages/`, `packages.sha256`, `install-order.txt`,
`roots.txt` and `target.txt`. MD5 verifies the existing pkgtools payload
contract. SHA256 identifies the copied archives. Neither is an upstream
signature verification. The audit does not install or run package scripts.

## Regression

The regression creates small archives with real `pkg_create`. It copies their
metadata into an isolated test database and resolves it with real `pkg_info`.
It does not modify the build sysroot or inspect the complete desktop closure.

```sh
PKG_CREATE=/absolute/native/pkg_create PKG_INFO=/absolute/native/pkg_info \
BSDTAR=/absolute/native/bsdtar \
    ruby probes/plasma-mobile/toolkit/tests/package-set.rb /absolute/new-tests
```

The 14 cases include PAX paths and link targets longer than the ustar limits,
hard links, dependency order and copied SHA256. Negative cases cover a stale
manifest, wrong archive architecture or OS version, modified payload bytes,
changed symbolic links, missing or unlisted payload, changed metadata, missing
dependencies and truncated archives. A valid later cache candidate is accepted.
Duplicate roots are rejected. An existing completed output is not replaced.
Failed audits leave no final set.

The implementation reads PAX records by their byte lengths. Libarchive converts
supported input compression to a stream; no package payload is extracted.
Sparse members, non-file special devices, metadata above 16 MiB and PAX size
overrides not represented by the tar header are explicitly rejected.

This is a package integrity and closure check. It does not prove that target
ELF objects load, that ABI metadata is truthful, or that Plasma renders.
Those checks require the separate target acceptance scenario. No C/C++ source
is changed. Cppcheck and compiler path analyzers do not analyze this Ruby code;
the regression is not a Valgrind run.

Origin: EmberBSD (AI-assisted).
