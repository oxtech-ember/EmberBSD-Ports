# GLAD provider provenance

This recipe replaces the upstream pkgsrc GLAD 1 recipe with Dav1dde/glad
v2.0.8, the current release. GLAD 2 changes the generated API; the current
export has no other GLAD consumers. There is no GLAD 1 compatibility wrapper.

The upstream Python generator and packaged Khronos XML are used at build time
with `REPRODUCIBLE`, so generation does not download or copy generated C files
into Ports. The installed shared target exports as `glad::glad` and provides
OpenGL compatibility 4.6, EGL 1.5, GLX 1.4 and WGL 1.0 with all extensions
supported by the pinned XML. GLX is built with `GLAD_GLX_NO_X11`, which
suppresses its XOpenDisplay path. Its public GLX header still includes X11
types, so the buildlink exposes libX11 and xorgproto headers as build-only
dependencies; the shared object has no libX11 runtime dependency.

The source generator is MIT licensed. The generated code is marked
`(WTFPL OR CC0-1.0) AND Apache-2.0`; the package chooses the CC0 option and
retains the upstream license text.
