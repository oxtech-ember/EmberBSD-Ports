# GN for native build generation

The canonical recipe is `pkgsrc/devel/gn`. It pins GN commit
`641ace93dd9560e75e7add0d08f77b446fbb3b78`. Published Chromium tag
[`152.0.7977.167`](https://chromium.googlesource.com/chromium/src/+/dd78960ccd8a03a2fe1f629543d27783885b78e9/DEPS)
selects this revision in `DEPS`.
The GN Git history reports `initial-commit-2486-g641ace93dd95`.
The package version is `2486`. Do not substitute the latest GN revision.

The official source is the exact
[GN commit archive](https://gn.googlesource.com/gn/+archive/641ace93dd9560e75e7add0d08f77b446fbb3b78.tar.gz).
The complete archive must match `distinfo`. It contains files at its root,
so the recipe sets `EXTRACT_DIR` to `WRKSRC`.

The existing Ports exporter discovers `pkgsrc/devel/gn` as an overlay recipe.
It maps that directory to `devel/gn` in the composed pkgsrc tree. No
`export.conf` entry or `pkgsrc/replaces` entry is needed. The pinned upstream
pkgsrc tree has no `devel/gn` recipe. Export collision checks remain enabled.

## Source changes

The patch to `build/gen.py` has three changes:

- On POSIX, the GCC probe passes the selected C++ command as an argument vector.
  It does not invoke a system shell. The Windows command route is unchanged.
- `GN_VERSION` supplies the recorded commit position and short hash when the
  source archive has no `.git` directory. The complete string is validated.
  The ordinary Git checkout route and the generated header format remain intact.
- Explicit Darwin `-mmacosx-version-min=` flags remain unchanged in the compile
  and link command. The upstream minimum version `14` is added only when that
  command has no explicit deployment minimum.

The archive-version approach follows
[FreeBSD devel/gn](https://cgit.freebsd.org/ports/tree/devel/gn/files/patch-build_gen.py).
The source keeps the Chromium copyright and BSD-style license. The FreeBSD
and [OpenBSD recipe](https://cvsweb.openbsd.org/ports/devel/gn/Makefile) were
reviewed for the Python, Ninja, archive-version and upstream-test routes.
Their source versions and platform patches are not copied into this recipe.

## Build and acceptance

Use the native Ports GCC16 prefix for a native GN build.
Select it with the SDK `load_host_prefix` API and required roles `cxx`, `ar`,
`python`, `ninja`, `sh`, `rm` and `make`. No producer receipt is required.
Use its compiler ABI flags and selected tool paths in the native pkgsrc configuration.
Keep the native package prefix separate from the EmberBSD target sysroot.
The Python and Ninja tool dependencies run on the build host. The C++ and
archive commands compile for the selected package target.

For native Darwin, the recipe runs these source-owned operations:

1. Selected Python runs `build/gen.py --platform darwin --host darwin`.
   `CXX` and `AR` select selected Ports tools. `GN_VERSION` is
   `2486 (641ace93dd95)`. The selected C++ flags include the SDK preprocessor
   and C++ ABI flags. Link flags remain the selected native link flags.
2. Selected Ninja runs `-C out -j 18 gn` for a jobs-18 build.
3. The test phase separately builds `-C out -j 18 gn_unittests`, then runs
   `out/gn_unittests`. The Python tool fragment supplies the selected native
   `python3` alias used by the upstream process test.
4. Installation copies `out/gn`, `LICENSE` and `README.md` through the pkgsrc
   program and data installation commands.

Each Ninja invocation has one executable link. Keep the existing global heavy
link lock for each invocation when using the SDK process API directly.
Do not start the default `all` target beside the test target. Keep the existing
owned-process deadline, drainage, input leases and MemoryWatch policy.
The recipe retains upstream warnings as errors. It does not select the
Clang-specific LTO option. Selected Darwin SDK deployment flags and G++ runtime defaults remain visible
for the actual ABI and runtime checks.

For cross packages, `--platform` uses `LOWER_OPSYS` and `--host` uses
`NATIVE_LOWER_OPSYS`. The recipe does not run the target executable during
configure or build. The test target refuses host execution of a cross-built
`gn_unittests`; run it on the matching target instead.

After the native package build, check `gn --version` against
`2486 (641ace93dd95)`. Run the upstream unit tests and a small GN-to-Ninja
project. Use `--script-executable=<selected native Python>` for GN generation.
For optional Ninja post-processing, pass
`--ninja-executable=<selected native Ninja>` explicitly.
Verify the installed Mach-O architecture, compiler identity, load commands
and complete runtime closure before adding the `gn` role to an SDK bundle.
Use the existing native provider build receipt and native toolset validation.
No new qualification format is defined here.

## Source regression

Run the pure regression with the exact downloaded source archive:

```sh
python3 profiles/common-build-tools/tests/test-gn-recipe.py \
  --archive /absolute/path/641ace93dd9560e75e7add0d08f77b446fbb3b78.tar.gz -v
```

It checks the archive and patch checksums, exact patch context, POSIX compiler
argument preservation, the Windows route, compiler macro failures, version
header identity, malformed version refusal and Darwin SDK minimum preservation. It executes extracted Python
functions with mocked child calls. It does not run a compiler, GN or Ninja.
Native build, package lifecycle, upstream test and installed runtime acceptance
remain pending.
