# HarfBuzz ICU integration

This split package uses the common `fonts/harfbuzz/Makefile.common` source,
version and patches, and installs the ICU integration library.

Its aarch64 GI dump was captured from the real Clang 23.1.4 build in an
EmberBSD guest with matching base/kernel revision
`2e5ec0754fdc95131d7b5de79b71526821be76c5`. The normal cross build replays it
through the shared launcher; capture and identity checks follow the
[GI procedure](../../../profiles/common-graphics/cross/gi-dumps.md).
