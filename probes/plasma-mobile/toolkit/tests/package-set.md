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
    /absolute/new-package-set plasma6-plasma-desktop-6.8.0nb4
```

Select the root name from the actual installed database. The example version
is illustrative. The command performs these checks before publishing output:

- Resolve every dependency to exactly one installed package. Reject cycles.
- Match each archive's `+CONTENTS` with the installed manifest.
- Check the archive's `OPSYS`, `OS_VERSION`, `MACHINE_ARCH` and `OBJECT_FMT`.
- Match every declared metadata file with the installed copy.
- Reject host paths in serialized `+INSTALL`, `+DEINSTALL` and `+REQUIRE`
  interpreters and helpers. Check the original archive before copying it.
- Require each `PROVIDES` path to exist in the package manifest.
- Reject `REQUIRES` paths supplied by the same package. `pkg_add` checks
  requirements before extraction, also when replacing an installed version.
- Require each `/usr/pkg/` requirement to name payload in the selected set.
  A packaged SONAME alias is accepted. A different major version is not inferred.
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

The 18 cases include PAX paths and link targets longer than the ustar limits,
hard links, dependency order and copied SHA256. Negative cases cover a stale
manifest, wrong archive architecture or OS version, modified payload bytes,
changed symbolic links, missing or unlisted payload, changed metadata, missing
dependencies and truncated archives. A valid later cache candidate is accepted.
Duplicate roots are rejected. An existing completed output is not replaced.
Matching database and archive metadata must still reject a missing provider
or a self-required regular file or symbolic link. Valid provider paths and
external requirements remain accepted. Failed audits leave no final set.
The valid fixture includes an explicit `.so.8` alias and a base `/usr/lib/`
requirement. A consumer that requires `.so.7` fails when its declared provider
packages only `.so.8`, even if both archive and database metadata agree.

The separate script regression uses the same real archive auditor:

```sh
PKG_CREATE=/absolute/native/pkg_create PKG_INFO=/absolute/native/pkg_info \
BSDTAR=/absolute/native/bsdtar \
    ruby probes/plasma-mobile/toolkit/tests/package-install-scripts.rb /absolute/new-script-tests
```

Its 20 cases cover all three script names, embedded helper scripts, quoted and
unquoted assignments, dot components, host roots, executable prefix boundaries,
archive/database disagreement and the absence of copying before rejection.
System paths, `/usr/pkg`, `/usr/local`, `/usr/X11R7` and the package's declared
prefix remain valid. Host paths in historical `+BUILD_INFO` remain valid too.
`PYTHON_PACKAGE_SCRIPT` can name an existing broken serialized script for an
additional negative case. `TARGET_PACKAGE_SCRIPT` adds a repaired positive case.
Both files are read as data. No package script is executed.

The gate checks literal shebang paths and pkgsrc's serialized helper assignments.
It also rejects known host roots in literal absolute assignments. It does not
resolve shell variables, command substitutions, `PATH` commands or symlinks.
This is a cross-package portability check, not a shell security audit.
Custom runtime logic still needs its own target lifecycle tests.

The implementation reads PAX records by their byte lengths. Libarchive converts
supported input compression to a stream; no package payload is extracted.
Sparse members, non-file special devices, metadata above 16 MiB and PAX size
overrides not represented by the tar header are explicitly rejected.

The package-managed requirement gate correlates metadata with exact manifest
paths in the selected closure. It does not inspect ELF `DT_NEEDED`, infer ABI
compatibility, resolve arbitrary filesystem aliases, or validate base-system
requirements outside `/usr/pkg/`. Those base paths require a separately verified
matching EmberBSD sysroot and target loader checks.

This is a package integrity and closure check. It does not prove that target
ELF objects load, that ABI metadata is truthful, or that Plasma renders.
Those checks require the separate target acceptance scenario. No C/C++ source
is changed. Cppcheck and compiler path analyzers do not analyze this Ruby code;
the regression is not a Valgrind run.

Origin: EmberBSD (AI-assisted).
