# Prepared wpa_supplicant source

This package installs the `src` subtree from the same wpa_supplicant release
and complete Ports patchset as `net/wpa_supplicant`, plus its license. The
shared location is `WPA_SUPPLICANT_SOURCE_DIR` from the owner's
`Makefile.common`. It supplies source to consumers; it does not configure a
supplicant or select a crypto implementation, host compiler, target ABI or
runtime. Consumers remain responsible for those choices.
