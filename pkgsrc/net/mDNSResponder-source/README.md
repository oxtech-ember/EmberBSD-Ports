# Prepared mDNSResponder source

This package supplies the same mDNSResponder release and complete Ports patch
set as `net/mDNSResponder`. `MDNSRESPONDER_SOURCE_DIR` in the owner's
`Makefile.common` names its shared source directory. It does not select a
compiler, target, ABI or mDNS policy. Consumers select these independently.
