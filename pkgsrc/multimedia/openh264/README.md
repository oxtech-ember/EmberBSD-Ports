# openh264

This common recipe selects [openh264 2.7.0](https://github.com/cisco/openh264/releases/tag/v2.7.0),
released on 2026-10-22. It includes upstream decoder bounds checks, hang
fixes and memory-safety fixes that 2.6.0 lacks. The release keeps SONAME
`libopenh264.so.8`. The pkgsrc ABI dependency floor is 2.7.0, so no consumer
accepts an older package. The recipe retains the NetBSD pkgsrc attribution,
its three upstream pkgsrc patches, and the upstream BSD license. The archive
is fetched through the ordinary pkgsrc fetch and recorded in `distinfo`.

The upstream Makefile takes `OS` from the build host `uname`. A cross build on
macOS therefore used `build/platform-darwin.mk` and Mach-O link flags. Cross
builds pass the target `OS`.

Consumers use the buildlink3 file without a version of their own:
`graphics/libheif`, `multimedia/gst-plugins1-openh264`, `www/chromium`,
`www/qt6-qtwebengine` and `x11/qt5-qtwebengine`.

## Regression

`tests/cross-os.py` checks that a cross configuration passes the target `OS`.
`tests/release.py` patches the source and checks the release floor, the PLIST
SONAME and the ABI floor:

```sh
python3 -B pkgsrc/multimedia/openh264/tests/release.py \
    --pkgsrc /absolute/export --makeconf /absolute/mk.conf --bmake /absolute/bmake
python3 -B pkgsrc/multimedia/openh264/tests/cross-os.py --pkgsrc /absolute/export \
    --makeconf /absolute/cross.mk.conf --work /absolute/new-dir --bmake /absolute/bmake
```
