# ZoneMinder PicoJSON integration

This recipe retains the complete pinned pkgsrc ZoneMinder 1.38.4 recipe and its existing patches.
Revision 3 selects the common PicoJSON provider through `JWT_EXTERNAL_PICOJSON`.
The bundled JWT consumer's external target had a trailing `>`; the patch corrects that spelling.
Both JWT include sites use the provider's public `picojson.h` layout.
The provider header matches the former bundled header byte for byte.
No source API or JSON behavior changes are intended.

The dependency-source gate is `../../devel/cppcheck/tests/dependencies.py`.
It replays all recipe patches and checks the external option, target and header paths.
Full ZoneMinder builds, JWT execution and package lifecycle are not covered by that source check.
Other bundled dependencies remain outside this PicoJSON migration.
The new integration changes are AI-assisted EmberBSD work.
