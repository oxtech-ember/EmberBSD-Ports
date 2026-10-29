# Common tcpdump source

The helper prepares the complete shared tcpdump release archive with the full
exported pkgsrc patch inventory. Native OS and package consumers share these
inputs while retaining their own build and installation interfaces.

The upstream 4.99.6 release removed OTV decoding after the corresponding
Internet-Draft became inactive; this remains absent in 4.99.7. The native
NetBSD integration keeps its separate installation paths and optional PF
support.
