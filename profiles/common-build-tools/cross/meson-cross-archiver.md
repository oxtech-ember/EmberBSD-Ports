# Meson cross archiver

For an EmberBSD SDK cross build, the common Meson integration places the
selected `TOOLS_PATH.ar` in the cross file. This is a host executable that
archives target objects. An explicit `MESON_BINARY.ar` remains authoritative.
Meson must not discover a target `llvm-ar` executable in a buildlink directory.
Native and unrelated pkgsrc cross configurations keep their existing policy.

[meson-cross-archiver.py](../tests/meson-cross-archiver.py) checks the selection fragment using SDK family
metadata, an override and a synthetic cross guard. It does not test the actual
framework guard or a complete Meson configuration. A real cross tool should
also archive and link a target object during validation.
