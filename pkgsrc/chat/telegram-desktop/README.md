# Telegram Desktop 7.3.5: package integration (work in progress)

The upstream full-source archive `tdesktop-7.3.5-full.tar.gz` is released at
https://github.com/telegramdesktop/tdesktop/releases/tag/v7.3.5 with SHA-256
`6acaf84b63a8bdcea06d928b4cee12a0dce68f17e88417ef8e988b953144fbd7`.
It contains third-party code and is not itself an assertion that dependencies
are supplied by Ports. Its GPL-3.0 and component license notices must be retained.

The recipe must use the shared target Qt 6, FFmpeg, OpenSSL, Opus and other
Ports libraries and native generators. `DESKTOP_APP_USE_PACKAGED` alone does
not enforce this: several upstream CMake modules quietly fall back to bundled
sources, while `cmark_gfm` and `microtex` always build copies. Local consumer patches
select the common providers; the full exported graph still needs validation.

The recipe selects common Ports providers for Qt 6, FFmpeg, OpenSSL, Opus,
VPX, OpenH264, RNNoise, ADA URL, Boost, range-v3, expected, xxHash, GSL,
QR generation, cmark-gfm, hunspell, CLD3, MicroTeX, TooManyCooks, tg_owt,
tde2e, and the combined tdesktop-rust wallet and animation provider. The
latter exports one target Rust archive and generated C++ bindings. Dependency
resolution and independent host/target roles remain the responsibility of the
shared Ports graph; amd64 and aarch64 remain in scope.

Native language, emoji and style generators are provided by the sibling
`chat/telegram-desktop-codegen` recipe from this same source and patch set.
The cross build selects those host tools explicitly. CppGir similarly uses a
native generator and target headers and GIR data. Packaged-mode checks reject
bundled fallbacks for the covered dependencies.

The individual providers have been built and checked, including target
consumers. This does not establish acceptance of the complete application or
of physical camera capture.

Upstream requires an application-specific Telegram API ID/hash for deployment
(`docs/api_credentials.md`). `TDESKTOP_API_TEST=ON` selects upstream test-only
credentials and must be restricted to a non-deployment diagnostic build; this
mode does not establish login acceptance. Release identity is supplied explicitly,
not committed as a personal credential. The package is not yet build- or
runtime-accepted.

For the NetBSD diagnostic build, upstream's `LINUX` CMake variable selects the
Unix desktop UI sources (as in the FreeBSD port). It does not change the target
OS or preprocessor identity. The WebRTC target explicitly selects
`WEBRTC_NETBSD`; the selector also enables upstream GTK/DBus, XDG, Pango and
spellchecking branches. Linux-specific APIs in those branches remain subject to
actual NetBSD build and runtime checks.
