# Plasma Activities service

This recipe selects kactivitymanagerd 6.7.5 with the common Plasma 6.7.5 stack.
Its source archive comes from the official KDE release directory.
The SHA256 matches the adjacent upstream `.sha256` file.
See the toolkit `sources.tsv` for the source URL and hash.

The recipe, package list and description come from pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`.
Original pkgsrc RCS identifiers and upstream licenses are retained.
The EmberBSD recipe delta is AI-assisted and has not been submitted upstream.

PlasmaActivities calls `StartServiceByName` for `org.kde.ActivityManager`.
The daemon supplies that session-bus service and the Activities methods.
The Plasma Desktop package must depend on this daemon at runtime.
The generated D-Bus service executes the installed `libexec/kactivitymanagerd`.
Its ordinary D-Bus activation does not require systemd.
The upstream systemd unit remains package data for platforms that use it.

Qt6 DBus tools and ECM provide the generated source and service files.
The recipe uses the common cross-build settings and target Qt6 plugin path.
It preserves all upstream daemon plugins and the inherited MOC include fix.
The generated package version header uses a unique name.
This prevents a collision with the protocol header `Version.h` on case-insensitive hosts.
The D-Bus protocol version and behavior stay unchanged.
See the [compile regression](../../../tests/activitymanager-version.md) for the check and analysis limits.

Source and recipe checks do not establish package or runtime acceptance.
Build with the normal package checks before installation.
On the target, check session-bus activation, activity creation and removal,
and restart persistence in a private user profile.
A complete Plasma shell session remains a separate acceptance step.
