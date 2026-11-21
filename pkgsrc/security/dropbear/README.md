# Dropbear

`security/dropbear` keeps the upstream pkgsrc default build and package name.
The sibling `security/dropbear-appliance` uses the same source, patch set,
distinfo, build rules, and file list. It is a static variant with server and
client agent forwarding disabled; upstream already defaults server X11
forwarding off. The two package names conflict because they share installed
paths.

The appliance profile should copy only `sbin/dropbear` and
`share/examples/rc.d/dropbear` into its image. Provision the pinned host key
separately and run without `-R`, so startup never creates a host key.
