# Cinnamon port

The active source control set is the stable Cinnamon 6.8 series in
[`probes/cinnamon-stable`](../cinnamon-stable/README.md). Its release pins
are recorded in [`sources.tsv`](../cinnamon-stable/sources.tsv).

The earlier 6.7 development snapshot is not the target for this port. The
stable source set includes Cinnamon Menus 6.8.0 and CJS 140.3. Source-level
checks cover CJS locale portability. The last published validation of the
CMenu GIR and typelib used the earlier 6.6.0nb3 package. Other components
still need package recipes and target checks.

GTK 3 is excluded from the accepted Cinnamon dependency closure. Keep it out
of package buildlinks, generated GIR/typelib imports and runtime requirements.
Patch or remove upstream GTK 3-only components in Ports.

The complete CJS shell and Cinnamon session require a real operating-system
`uselocale()` implementation. The current EmberBSD libc does not provide
that interface. See the stable README and validation record for the current
port boundary.
