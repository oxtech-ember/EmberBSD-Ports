# Dropbear appliance package

This sibling PKGPATH builds a static Dropbear package from the shared
`security/dropbear` recipe, distfile, patches and file list. Its `localoptions.h`
profile disables server and client agent forwarding; X11 forwarding is off in
upstream defaults. The package name is `dropbear-appliance-2026.94` and it
conflicts with the ordinary package because they install the same paths.

For appliance images, stage only `sbin/dropbear` and
`share/examples/rc.d/dropbear`. Provision a pinned host key separately and
run without `-R`, so startup never creates a host key.
