# Common U-Boot sources

`u-boot-source` installs the patched U-Boot release under
`share/u-boot-source`. It prepares source only; it does not build or install
firmware, select a board, or change the version used by existing U-Boot
packages.

The package applies the owner patch set and board files, then populates the
U-Boot libfdt and zlib integration from the shared `dtc-libfdt-source` and
`zlib-source` packages. U-Boot's `libfdt_env.h` remains its integration adapter.
A firmware consumer should include `Makefile.common`, declare the matching
source package as a build tool dependency, copy the installed source into its
own work directory and select host and target tools separately.

The source package does not establish board, image-format or runtime support.
The embedded upstream Mbed TLS source is excluded. A consumer enabling its
backend must populate `lib/mbedtls/external/mbedtls` with a compatible source
prepared by the common Ports owner, including its complete patch set, before
building. Selecting that backend without the source stops the build explicitly.
This receiver does not establish Mbed TLS backend compatibility or support.
