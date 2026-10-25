# NetBSD configured compiler seed runtime policy

This template applies only to an independently admitted GCC 16.2 bootstrap
seed on NetBSD 11 amd64. It is not an ordinary compiler profile.

The retained compiler's configured `link_libgcc` spec adds its original
installation paths as runtime search paths. A copied compiler still emits
those paths. This template retains GCC's `%D` library search expansion and
removes the historical default runtime paths. It preserves collect2, the
normal link command, CRT selection and plugin handling.

The SDK must pin these exact bytes and the selected Ports revision. It must
copy the template into the admitted seed bundle and pass `-specs` explicitly.
Initial C and C++ link commands also select static GCC runtimes with
`-static-libgcc` and `-static-libstdc++`. The latter applies to C++.
The native host ABI libraries remain explicit inputs.

`../tests/netbsd-configured-seed-runtime.py` checks actual driver dry runs
and archive queries without compiling or linking a program. These checks
do not qualify a compiler or replace a finite runtime pilot. Independent
seed admission and final output ELF/runtime checks remain required.
The report hashes the original and overridden traces. It does not observe
external assembler or linker execution; those need separate source and
configured-route evidence, followed by the accepted finite pilot.
