# 3DxWare SDK subset provenance

This package extracts the maintained subset from KiCad 10.0.8
`thirdparty/3dxware_sdk`. KiCad identifies it as part of 3Dconnexion 3DxWare
SDK v4. The full vendor SDK is separate and is not included. The extracted
headers and loader sources carry GPL-3.0-or-later notices; the package installs
KiCad's GPLv3 license text.

The package exports `3DxWare::Navlib` and `3DxWare::headers` through the
`TDxWare_SDK` CMake config package. The non-Windows, non-Apple loader returns
`EOPNOTSUPP`; it is a compatibility stub, not a hardware driver. Unix
SpaceMouse support remains a separate libspnav interface.
