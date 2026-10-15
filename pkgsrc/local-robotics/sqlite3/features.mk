# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Common SQLite features from the pkgsrc policy.
SQLITE_CONFIGURE_ARGS= --enable-threadsafe --fts3 --fts4 --fts5 --rtree --geopoly --column-metadata --dbstat --enable-math --disable-readline --disable-static-shell --soname=legacy
SQLITE_CPPFLAGS= -DSQLITE_ENABLE_FTS3_PARENTHESIS -DSQLITE_ENABLE_HIDDEN_COLUMNS
