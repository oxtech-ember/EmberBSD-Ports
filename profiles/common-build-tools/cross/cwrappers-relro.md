# RELRO on wrapped links

pkgsrc adds the RELRO linker flags to `LDFLAGS`. Some recipes link with
their own commands and do not use `LDFLAGS`. Their binaries have no RELRO
segment, and `check-relro` stops the package with "missing RELRO".

The patch `patches/pkgsrc-cwrappers-relro-link.patch` writes the selected
`_RELRO_LDFLAGS` into the C, C++ and Fortran wrapper configuration as
`append_executable` and `append_shared` arguments. The wrapper adds them only
when it links an executable or a shared object. Compile-only commands do not
change. `MKPIE` uses the same wrapper mechanism.

The flags come from the same pkgsrc settings as before: `PKGSRC_USE_RELRO`,
`RELRO_SUPPORTED` and the platform support. A recipe that sets
`RELRO_SUPPORTED=no` gets no flags. Platforms without RELRO support, such as
the Darwin build host, are not affected. Recipes that already use `LDFLAGS`
get the same flags twice, and the linked output does not change.

Regression: `tests/cwrappers-relro.sh EXPORTED_PKGSRC` runs the wrapper
phase of `www/http_load` with the cross `MAKECONF`. It requires the RELRO
flags in the `cc`, `c++` and `f77` configurations, and no flags when
`PKGSRC_USE_RELRO=no`. Without the patch the test fails. With
`PKG_DEVELOPER=yes` and without the patch, the `www/http_load` package stops
with "bin/http_load: missing RELRO". With the patch the package is created.
