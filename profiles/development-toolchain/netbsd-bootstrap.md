# NetBSD first-native bootstrap profile

The NetBSD first-native profile is a Ports-owned, opt-in policy for a native
NetBSD 11.0 amd64 host. It is intended only for the first source-built GCC 16
toolchain and its ordinary native tool foundation. It does not change installed
EmberBSD systems or the laptop configuration.

The SDK validates the host facts, selected tools, utility directory and output
paths, then writes MAKECONF with the exported
`EMBERBSD-NETBSD-BOOTSTRAP-MK.CONF` include. pkgsrc reads that file
before host/tool discovery. The profile fixes pkgsrc's host architecture to
`x86_64`, routes make, the actual bmake recipe shell, compilers, binutils and
parse-time utilities through the accepted input tuple, and rejects cross mode
and jobs greater than one. The bootstrap-mk-files seed installs the shell
builtin dispatcher used by later package recipes. The GCC16 package receives
source dependencies on binutils, bmake, gmake, mksh and Python 3.15. The
profile also selects the source-built makeinfo and compression tools, plus
candidate edges for common pkgsrc utilities. Their full transitive dependency
and tool closure is not yet qualified.

For this scoped GCC package, pkgsrc uses the source-built
`${LOCALBASE}/bin/gas` and `${LOCALBASE}/bin/gld`. The ordinary NetBSD recipe
keeps its base assembler/linker selection and bootstrap workaround. The
profile omits the workaround so that the compiler's actual stage2/stage3
comparison remains active.

No seed C++ runtime link flags are selected here. Their NetBSD driver support
and resulting ELF/RPATH closure require a real link from the accepted seed and
must be measured before the first C++ foundation provider is built. Metadata
tests do not qualify those runtime outputs or an ordinary NativeToolset.

The source regression `tests/netbsd-bootstrap-profile.py` evaluates the real
pkgsrc profile and GCC16 `Makefile.common` with the accepted bmake. It checks
the shell actually used by a recipe, installation and PLIST registration of
the builtin dispatcher, its echo/true/false/test/[ behavior, profile host/mode
guards, compiler/binutils routes, direct profile dependency edges and ordinary
NetBSD behavior. It never starts a package build or compiles C/C++ code. Package
metadata may query the selected compiler's identity. The test follows real
pkgsrc Makefiles through the native source dependency graph, rejects cycles,
and checks each selected dependency pattern against the provider's evaluated
`PKGNAME` with an explicitly path- and SHA256-pinned `pkg_admin pmatch` query.
That query is metadata-only and does not install packages or write the package
database. The graph result does not qualify package builds, runtime libraries,
ELF closure or an ordinary NativeToolset; those remain separate admission
checks before source builds start.
