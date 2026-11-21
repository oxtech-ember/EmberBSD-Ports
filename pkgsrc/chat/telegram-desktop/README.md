# Telegram Desktop 7.4.4: package integration (diagnostic work in progress)

The upstream full-source archive `tdesktop-7.4.4-full.tar.gz` is released at
https://github.com/telegramdesktop/tdesktop/releases/tag/v7.4.4 with SHA-256
`b563b3a35a5589f70f317297aa8dc4f19da065c393c3ae663ae11841b5ab0891`.
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

Native language, emoji, style and password-dictionary transliteration generators are provided by the sibling
`chat/telegram-desktop-codegen` recipe from this same source and patch set.
The cross build selects those host tools explicitly. All four native generators
were run against the 7.4.4 inputs; the check verified ten generated files and
the Cyrillic dictionary transliteration output. CppGir similarly uses a native
generator and target headers and GIR data. Packaged-mode checks reject bundled
fallbacks for the covered dependencies.

QuickJS uses the pinned TelegramMessenger fork through the shared
`lang/quickjs-ng` provider, kept distinct from Bellard QuickJS. The Telegram
consumer builds the widget-sandbox C shim and links the provider library; other
platforms retain upstream's source build. The actual 7.4.4 CMake consumer and
shim compiled and linked for the target. In the AArch64 runtime VM, the official
sandbox and validator `.qbc` bundles initialized successfully and both rejected
a mismatched source stamp. This runtime harness supplied no-op host hooks, so
it did not exercise production host integrations.

The vendored Twidget renderer also uses the shared `www/litehtml` provider and
its system Gumbo dependency. Its updatable and initial parse paths both select
`parse_mode::bounded_widget`. The actual bundled renderer compiled as both a
Darwin arm64 object and an EmberBSD AArch64 object. The target Qt consumer and
bounded-depth policy probe passed in the AArch64 VM.

The full 7.4.4 AArch64 client build remains diagnostic work. This check does
not establish messaging, login or physical camera acceptance.

Upstream requires an application-specific Telegram API ID/hash for deployment
(`docs/api_credentials.md`). `TDESKTOP_API_TEST=ON` selects upstream test-only
credentials and must be restricted to a non-deployment diagnostic build; this
mode does not establish login acceptance. Release identity is supplied explicitly,
not committed as a personal credential. The release package and runtime remain
unaccepted; the recipe keeps its diagnostic install guard and does not publish
the client package while dependency integration is incomplete.

The Unix desktop package list follows upstream's packaged-mode CMake install
rules: the executable, application entry, hicolor and symbolic icons, D-Bus
service and AppStream metadata. It also retains the application's license and
notices for the compiled Desktop App Toolkit, libprisma and tgcalls code, the
portal interface definitions and the application password dictionary. The
desktop database and icon cache use the existing pkgsrc install hooks. The
actual release stage, component attribution and package lifecycle still need
verification with a release identity; the diagnostic install guard remains in
force.

For the NetBSD diagnostic build, upstream's `LINUX` CMake variable selects the
Unix desktop UI sources (as in the FreeBSD port). It does not change the target
OS or preprocessor identity. The WebRTC target explicitly selects
`WEBRTC_NETBSD`; the selector also enables upstream GTK/DBus, XDG, Pango and
spellchecking branches. Linux-specific APIs in those branches remain subject to
actual NetBSD build and runtime checks.
