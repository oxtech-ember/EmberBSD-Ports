# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Common SQLite features from the pkgsrc policy.
SQLITE_CONFIGURE_ARGS= --enable-threadsafe --fts3 --fts4 --fts5 --rtree --geopoly --column-metadata --dbstat --enable-math --session --enable-load-extension --disable-static-shell
SQLITE_CPPFLAGS= -DSQLITE_ENABLE_FTS3_PARENTHESIS -DSQLITE_ENABLE_HIDDEN_COLUMNS -DSQLITE_ENABLE_STMTVTAB -DSQLITE_ENABLE_UNLOCK_NOTIFY
SQLITE_ELF_CONFIGURE_ARGS= --soname=legacy
