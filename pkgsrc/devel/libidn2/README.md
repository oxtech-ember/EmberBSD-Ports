# Libidn2 2.3.8

This recipe imports `devel/libidn2` from NetBSD pkgsrc commit
`eb32299952846914526cd34bd4e9b6d832395158`. Keep its NetBSD revision tags.

- Recipe: <https://github.com/NetBSD/pkgsrc/tree/eb32299952846914526cd34bd4e9b6d832395158/devel/libidn2>
- Release: <https://ftp.gnu.org/gnu/libidn/libidn2-2.3.8.tar.gz>

The source archive matches the upstream BLAKE2s, SHA512 and size entries.
The recipe retains the upstream ABI requirements, tests and platform rules.
It adds no source patch or compiler exception. Package and target execution
checks use the selected native or cross EmberBSD profile: Clang/LLVM by default,
with GCC selected explicitly for a platform requirement.
