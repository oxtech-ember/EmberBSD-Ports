# Common TDB source

`source.py prepare` extracts the pinned `databases/tdb` archive and applies the
complete exported package patch set. `verify-source` checks the prepared tree
and its effective package identity. Select the SDK source, absolute Git and
native patch executable explicitly; a changed recipe can be compared using the
archive and patch inputs. The source is shared by package and native OS consumers.
The package's pre-configure DocBook path substitution is not part of this
source preparation; consumers building its documentation use the package's
configure and tool routing.

The TDB library is LGPL-3.0-or-later; the package also contains GPL-3.0-or-later
command-line tools. Source selection does not establish target ABI or runtime
compatibility; those are checked by the consuming build and target tests.
