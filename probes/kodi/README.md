# Kodi for EmberBSD

This probe targets Kodi 21.3 Omega, the latest stable Kodi release at this
checkpoint ([21.3 release](https://kodi.tv/article/kodi-21-3-omega-release/)).
Kodi 22.0 Piers remains a prerelease at [RC 1](https://kodi.tv/article/kodi-22-piers-rc-1/).
The archive pin, upstream commit and licenses are in `source.json`. The package
is not complete.

The existing common PCRE2 10.49 provider replaces Kodi's bundled PCRE1 path.
The source changes follow Kodi's upstream PCRE2 migration and match-data
lifetime repair. The Kodi 21.3 API has two named-capture methods absent from the
upstream migration; the local patch adapts them. The EmberBSD ownership patch
also copies capture storage and validates match state;
the upstream lifetime change alone keeps a pointer into another expression's
match data. Both upstream changes retain their source commits in the patch
headers.

The allocation-failure patch checks compile-context, JIT match-context, and
match-data creation before use. The target regression wraps those PCRE2
factories and injects allocation failures. The cross executable includes these
checks, but it still needs execution in the EmberBSD acceptance VM. The JIT
match-context case reports a skip if the selected PCRE2 build cannot JIT the
test expression. The source also guards named-capture queries after a failed
compile and uses PCRE2's checked error offset for malformed UTF-8 diagnostics.
The baseline tests reproduce both the null-code dereference and capture
ownership failure. A fresh malformed-UTF-8 subject covers the error path.
The native process pins loader search to the selected prefix and checks that the
runtime library reports PCRE2 10.49.

`tests/check-regexp.py` extracts the real Kodi regular-expression consumer,
applies the pinned patches, builds baseline and repaired native controls with
AddressSanitizer and UndefinedBehaviorSanitizer, and cross-compiles the repaired
consumer with GCC 16.2 for AArch64 NetBSD. It compares Cppcheck findings against
the Kodi PCRE2-migration baseline and runs Clang Static Analyzer with the target
compile flags. The script checks source archives and every patch hash. Pass
paths from the local shared build root:

```sh
EMBERBSD_ROOT=/path/to/EmberBSD \
TMPDIR="$EMBERBSD_ROOT/tmp" \
  python3 probes/kodi/tests/check-regexp.py \
  "$EMBERBSD_ROOT/cache/distfiles/xbmc-21.3-Omega.tar.gz" \
  "$EMBERBSD_ROOT/cache/distfiles/fmt-12.2.0.tar.gz" \
  /absolute/native-pcre2-prefix \
  "$EMBERBSD_ROOT/work/ember-gcc16-toolchain" \
  "$EMBERBSD_ROOT/build/sysroot" \
  "$EMBERBSD_ROOT/build/obj/kodi-regexp" \
  --analyzer clang++
```

The runner derives the shared `build/obj` and temporary roots from the sysroot.
It refuses work paths outside `build/obj` and requires `TMPDIR` under the
shared temporary directory. It records the exact paths and available disk
space before extracting sources or compiling.

The native sanitizer run is not a Valgrind result. macOS does not provide the
LeakSanitizer mode selected by this script. The AArch64 executable still needs
execution in the EmberBSD acceptance VM. The comparison baseline includes the
upstream PCRE2 migration and the minimum named-capture API adaptation; the
Cppcheck database treats the separately pinned fmt headers as an external
system dependency.

The complete Kodi build is currently blocked earlier in upstream CMake
configuration. Kodi 21.3 has no NetBSD platform files, and its platform
selection fails before dependency checks. The package also needs a current
external fmt provider. A Kodi `FindPCRE2` module patch requires PCRE2 10.49
through pkg-config. A standalone CMake configure found the shared sysroot
package and created Kodi's expected imported target. This does not validate a
Kodi configure or package build. Do not map NetBSD to Kodi's FreeBSD backend or
enable the bundled legacy dependencies to pass configuration. The NetBSD platform,
complete dependency closure, ordinary GCC16 package build, installation, and
runtime playback remain unverified.
