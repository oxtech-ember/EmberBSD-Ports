# Shared tcpdump

This recipe supplies tcpdump 4.99.7 and retains the pkgsrc SSL and libsmi
options, privilege-drop configuration and package layout. The common source
helper applies the complete patch inventory for both package and native OS
consumers. NetBSD PF decoding and native startup policy are selected by the
OS producer; portable compatibility fixes are shared.

Upstream removed OTV decoding in 4.99.6 because its Internet-Draft became
inactive. This version does not provide that decoder.
