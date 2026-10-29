# Common libcroco source

The GNOME release archive identifies 0.6.13 as its latest release. The project
is archived; this recipe preserves pkgsrc's configure patch and applies the
complete libcroco C/header delta shipped with GNU gettext 1.0 libtextstyle.
That maintained GNU payload includes its copyright and LGPL notices. The
archive and embedded public configuration header both report 0.6.12 despite
the 0.6.13 distribution name; the actual API and dependencies must be checked
rather than inferred from that header string.

EmberBSD integration was AI-assisted. The common recipe retains the upstream
GLib and libxml2 dependencies; consumers must not substitute the unpatched
archive or an embedded private library.

The original distribution includes the LGPL 2.0 text while the source files
specify LGPL 2.1; both texts are installed. The GNU header notice is retained
in the configure template because the build regenerates the public header.
