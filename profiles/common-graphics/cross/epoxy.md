# Accept libepoxy against the common Mesa package

libepoxy is the first downstream consumer of the complete common Mesa26
package. Its [upstream stable release](https://github.com/anholt/libepoxy/tags)
remains 1.5.10, checked on 2026-10-08. The pinned pkgsrc recipe supplies
1.5.10nb2 and retains its EGL, GLX and X11 support. No second Mesa or LLVM
provider is introduced.

Use the [graphics cross composition](profile.md) and normal pkgsrc `package`
and sysroot installation targets for `graphics/libepoxy`. The target sysroot
must contain the accepted MesaLib 26.2.4nb9 package and LLVM 23.1.3.
The Python preparation requires that exact Mesa identity in the hash-verified
acceptance bundle. The current libepoxy package records the nb9 build provider
and the recipe's `MesaLib>=26.2.4nb4` dependency floor. Both are checked.
The older package's stale `xfixes`
pkg-config requirement and unused Xlib Xdamage/Xfixes buildlinks prevented
consumer configuration. The nb2 correction uses Mesa's actual `xcb-xfixes`
provider; no extra Xlib libraries are installed to conceal that metadata error.
Use a new consumer work directory after changing a provider's dependency
metadata. pkgsrc caches `.depends` and its resolved package identities.

On 2026-10-08, macOS/GCC16 cross-built the normal libepoxy package. File,
permission, PIE/RELRO, RPATH and work-reference checks passed. Its final
package dependency is `MesaLib>=26.2.4nb2`; normal cross-sysroot installation
also passed. The actual pkg-config module set compiles an epoxy-dispatched
pixel consumer. Installed acceptance on Orange Pi Zero 3W (A733), running
EmberBSD 11/AArch64, passes four llvmpipe/LLVM23 EGL lifecycles and all four
selected upstream invocations. It reports EGL 1.5 and GLES 3.2. Complete
package hashes, loader paths and live EGL/GLES/gallium/LLVM providers match
the installed canonical closure, without loader or driver overrides.

## Build and prepare the consumer

The host helpers use Python 3.15 and its standard library, without pip or
virtualenv. They do not add Python to the target runtime. These helpers use
no shared SDK Python API; that API is not published yet. The target runner
remains a NetBSD shell script. Set `CC` to the native GCC16 compiler for the
callback regression. Ruby callers of that regression select the same host
interpreter through `PYTHON` (default `python3.15`).

The existing `mesa-render.c` retains direct EGL/GLES headers by default.
`EMBER_EPOXY_DISPATCH` instead selects the installed epoxy headers and records
NetBSD's live loaded libraries after drawing. The compiler uses PIC/PIE so
libepoxy's dispatch-pointer imports remain undefined GOT entries rather than
COPY relocations. Its ELF must need libepoxy and GBM, have actual `epoxy_*`
imports, and have no direct EGL/GLES dependency.

```sh
# Preserve the default direct EGL/GLES build as a separate compile guard:
python3.15 ../tests/mesa-pkgconfig.py /absolute/cross-tools /absolute/sysroot \
    /absolute/host/bin/pkg-config /absolute/new-direct-consumer-work
python3.15 ../tests/mesa-pkgconfig.py /absolute/cross-tools /absolute/sysroot \
    /absolute/host/bin/pkg-config /absolute/new-epoxy-consumer-work epoxy
python3.15 prepare-epoxy-tests.py /absolute/cross-tools /absolute/sysroot \
    /absolute/libepoxy-1.5.10/output /absolute/libepoxy-1.5.10nb2.tgz \
    /absolute/accepted-mesa-bundle /absolute/new-epoxy-consumer-work \
    /absolute/new-epoxy-acceptance-work
python3.15 ../tests/epoxy-bundle.py /absolute/new-epoxy-acceptance-work/bundle \
    /absolute/sysroot /absolute/new-integrity-test-work
python3.15 ../tests/epoxy-loader-callback.py ./mesa-render.c \
    /absolute/new-callback-test-work
python3.15 ../tests/epoxy-bundle.test.py /absolute/cross-tools /absolute/sysroot \
    /absolute/libepoxy-1.5.10/output /absolute/libepoxy-1.5.10nb2.tgz \
    /absolute/accepted-mesa-bundle /absolute/new-epoxy-consumer-work \
    /absolute/new-preparation-regression-work
```

The Mesa bundle comes from [the installed package helper](mesa-package.md).
The libepoxy preparation verifies its complete installed Mesa manifests and
compares every libepoxy file and symlink with the normal package. It copies
only the consumer and four real unconditional upstream executables:
`header_guards`, `misc_defines`, `khronos_typedefs` and `gl_version`.
The last is upstream's version-parser unit test with its explicit mocked
version strings; actual rendering uses the separate pixel consumer.

Meson gives these upstream executables one build-library `LD_LIBRARY_PATH`.
Preparation accepts only that exact expected value, preserves the original
metadata and removes the override for installed-library acceptance. Other
unexpected test prerequisites fail. Display-dependent EGL/GLX tests are not
included. All executable RPATHs must use the canonical installed providers. Exact
upstream timeout values remain bounded to 1–120 seconds and are recorded
in `tests.tsv`. Duplicate or missing tests and extra environment settings
fail preparation.

The archive contains no runtime libraries. It records complete Mesa/libepoxy
file hashes, exact symlink targets, runtime hashes, source/command provenance
and every bundle artifact. Host integrity tests reject altered real consumer
bytes, an installed epoxy header and the installed epoxy DSO. The isolated
file fixture preserves the original sysroot.

The preparation regression copies real test executables and Meson metadata.
Its control accepts those inputs. Ten causal refusals cover wrong or duplicate
Mesa identities, invalid timeout values, missing or duplicate tests, extra
environment settings or arguments, and a changed ELF machine identifier.
Identity fixtures have updated local artifact hashes so refusal comes from
the package identity check. None of these host checks executes target code.

The callback regression executes the actual C callback with a labelled host
data fixture. Both exact NetBSD loader names, `/libexec/ld.elf_so` and
`/usr/libexec/ld.elf_so`, are valid. A foreign library returns a failure to
the iterator caller; process exit occurs only after iteration and EGL cleanup.
This catches the earlier helper refusal and its exit inside the callback.
It does not emulate the target loader or replace real rendering acceptance.

## Execute on NetBSD/AArch64

Install the exact normal Mesa and libepoxy packages and their dependencies.
Verify the transferred archive hash and extract it into a new directory:

```sh
sh /absolute/bundle/run-epoxy-tests.sh /absolute/bundle /absolute/new-target-logs
```

The runner verifies the complete payload before `ldd` or execution, rejects
loader/driver overrides and gives each child a clean environment. It checks
both direct loader dependencies and the providers reported by the live
process after libepoxy opens EGL/GLES. The pixel consumer must load the
recorded canonical libepoxy, EGL, GLES, gallium and LLVM libraries, reject
invalid GLSL, read correct triangle pixels and finish four llvmpipe EGL
lifecycles. Its limit is 60 seconds; each pure upstream test uses its recorded
Meson timeout (30 seconds in the accepted 1.5.10 build).
All invocations add a five-second forced-kill grace period. A target probe
with a child ignoring TERM verified the timeout's forced-kill behavior:
a one-second timeout and two-second grace ended with status 137 after three
seconds. The earlier helper failure and its target log remain separate from
the accepted run; no Mesa or libepoxy library rebuild was needed for that fix.

This checks the installed CPU renderer and dynamic dispatch without a DRM
device or display server. It does not establish a visible X11/Wayland session,
GLX behavior, a compositor or physical GPU acceleration. wlroots 0.20.2 and
labwc 0.20.2 are separate consumer migrations with additional dependencies.
