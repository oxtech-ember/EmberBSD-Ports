# Prepared dhcpcd source

This package supplies the same release and full Ports patch set as
`net/dhcpcd`. `DHCPCD_SOURCE_DIR` in the owner's `Makefile.common` names its
shared source directory. It does not select a compiler, target ABI or network
policy; consumers select those independently.
