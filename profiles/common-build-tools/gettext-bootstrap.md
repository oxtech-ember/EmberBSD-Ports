# Native gettext bootstrap composition

The common `devel/gettext-tools` recipe builds full color and CSS support by
default. Its `style` option selects the common libcroco, GLib and libxml2
libraries. The package dependency graph needs gettext tools to build GLib,
so a new native prefix first builds the same recipe with `-style`. Use this
stage before installing consumers linked to libtextstyle: replacing a full
package with the plain package removes that library. An existing prefix with
such consumers should retain its full package while the new full package is
built.

Use the ordinary selected native pkgsrc environment, package database and
prefix throughout. Keep separate object directories for the two option sets:

1. Build and install `devel/gettext-tools` with
   `PKG_OPTIONS.gettext-tools=-style`. This package supplies `msgfmt` and
   `xgettext`, with NLS and the common libxml2 dependency, without installing
   libtextstyle.
2. In the next stage's MAKECONF select the just-installed prefix programs:
   `EMBERBSD_BUILD_MSGFMT=<prefix>/bin/msgfmt` and
   `TOOLS_PLATFORM.xgettext=<prefix>/bin/xgettext`. Build or reuse compatible
   `devel/glib2` and `textproc/libcroco` packages from their common recipes.
3. Build `devel/gettext-tools` with `PKG_OPTIONS.gettext-tools=style`, using a
   fresh object directory and those same host-tool selections. Replace the
   temporary package using `pkg_add -U` in the same prefix. This explicit
   same-version replacement is required because the plain and full variants
   have the same package name and revision. Confirm the installed package's `PKG_OPTIONS` includes `style`
   using `pkg_info -Q PKG_OPTIONS`, and check the final package files.

The plain package is a bootstrap stage, not the completed default composition.
The staged host-tool choices do not replace target libraries or target tools.
An existing compatible GLib or libcroco package need not be rebuilt solely for
this sequence. The source-only dependency exporter describes the entire source
closure, including bootstrap dependencies; it is not the executor of these
installed-provider stages.
