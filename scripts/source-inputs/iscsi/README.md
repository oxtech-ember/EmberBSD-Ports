# Common NetBSD iSCSI source

The helper prepares the pinned NetBSD iSCSI 20111006 archive with the complete
maintained native source delta and pkgsrc portability patch set. The OS
consumer retains its native library ABI and build integration. Source integrity
and the archive and complete patch inventory are checked during preparation.

The package library SONAME is bumped because an exported internal send helper
changed from six to eight arguments in the maintained NetBSD source. Rebuild
package consumers against the new library. The OS retains its own SONAME 2.
