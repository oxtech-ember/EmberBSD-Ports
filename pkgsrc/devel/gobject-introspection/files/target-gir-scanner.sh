#!/bin/sh
# The native scanner and its Python module use the libraries of the build
# host. Meson points LD_LIBRARY_PATH at target build libraries, and the
# scanner adds its target link directories for the transient program. On a
# Linux build host that variable overrides the RUNPATH of native programs,
# including the compiler bindings. Pass the target directories to
# target-query.py in EMBERBSD_GI_LIBRARY_PATH instead.
unset LD_LIBRARY_PATH
exec '@GI_SCANNER@' --use-ldd-wrapper='@GI_LDD_WRAPPER@' \
    --lib-dirs-envvar=EMBERBSD_GI_LIBRARY_PATH "$@"
