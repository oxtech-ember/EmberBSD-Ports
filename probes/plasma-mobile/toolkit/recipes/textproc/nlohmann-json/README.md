# nlohmann-json 3.12.0

Version 3.12.0 remains the current stable release as checked on 2026-10-13:
<https://github.com/nlohmann/json/releases/tag/v3.12.0>.
The recipe derives from pkgsrc fff4deb639a1a640476203c80f752fb77b6cb14b.
Keep its MIT license and existing portability patches.

The default remains the header-only provider. The existing optional `tests`
option is preserved. It is not disabled to hide a build or test failure.
When selected, the recipe fetches upstream test data v3.1.0 through pkgsrc
checksums and passes `JSON_TestDataDirectory`. CMake does not clone the data.
The data archive is about 110 MiB; its tracked contents total 261,689,233 bytes.
Some upstream tests require a Git source checkout. A release-archive build
must report those limits separately from executable consumer checks.

Cross-built tests must run on EmberBSD. A header package and a CMake configure
pass do not prove the full upstream test corpus or a Fcitx input session.
The optional data-fetch adaptation is AI-assisted EmberBSD work.
