# DRM render-node discovery

The libudev-bsd 0.7.0.1nb1 recipe classifies decimal `/dev/dri/renderD*`
paths as DRM devices. It selects the existing DRM metadata handler.
Primary `card*` classification is unchanged. The public ABI is unchanged.

KWin 6.8 enumerates subsystem `drm` with sysname
`renderD[1-2][0-9][0-9]`. Upstream libudev-bsd 0.7.0.1 has no render-node
entry. Its filter rejects the unknown subsystem before checking the sysname.
The adaptation repairs the common provider. It does not select a fixed node
in KWin. The library accepts any decimal unit; the narrower KWin pattern
belongs to that consumer.

The patch rejects nondecimal suffixes and nested paths. A glob ending in
`[0-9]*` alone also accepts `renderD128x` and `renderD128/child`.
The upstream archive pin is unchanged. The patch is AI-assisted and local;
it has not been submitted or accepted upstream.

## Source contract

Run from the Ports checkout with Ruby and a host C compiler:

```sh
ruby profiles/common-graphics/tests/libudev-render-nodes.rb \
  /absolute/distfiles/libudev-bsd-0.7.0.1.tar.gz /absolute/new-test-work
CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' \
  ruby profiles/common-graphics/tests/libudev-render-nodes.rb \
  /absolute/distfiles/libudev-bsd-0.7.0.1.tar.gz /absolute/new-sanitized-work
```

The runner verifies the source archive and patch hashes. It compiles the
actual classifier, filter, list and utility sources. Host feature checks
select libc `strlcpy` and `strlcat` when available. GNU C is required by the
upstream fallback tree header. Unrelated hardware/property callbacks abort
if reached; they cannot fabricate a successful match.

The pinned source must reject `renderD128` after a successful compilation.
The patched source must pass 30 path cases and four filter lifecycles.
Cases include primary nodes, consumer range boundaries, long decimal units,
malformed names, wrong paths and negative subsystem filters.
ASan/UBSan covers this host contract. It does not exercise the BSD device
scanner or kernel. A sanitizer run is not a Valgrind Memcheck result.

## Target check

Cross-build `tests/libudev-render-enumerate.c` against the EmberBSD sysroot
and its packaged libudev. Use the [common cross configuration](profile.md).
Link with `-ludev` and the normal `/usr/pkg/lib` runtime search path.
Install the complete nb1 package through pkgsrc tools before acceptance.
Run the probe as the intended compositor user without loader overrides:

```sh
./libudev-render-enumerate
```

The program repeats the public enumeration and device API four times.
It validates subsystem, sysname, character-device type and device number.
It reports classification separately from `open(O_RDWR)` and its errno.
Static device nodes can exist without a live driver. Each cycle requires
at least one classified node and one successful open. No GPU ioctl or
rendering command is issued. The probe does not prove KMS support, hardware
rendering, compositor startup or a usable Plasma session.
