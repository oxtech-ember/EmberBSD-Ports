/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include "rename_exports.h"
#include "sqlite3.h"
#include <stdio.h>

int
main(int argc, char **argv)
{
	sqlite3 *db = NULL, *recovered = NULL;
	sqlite3_recover *rec;
	sqlite3_stmt *stmt = NULL;

	if (argc != 3 || sqlite3_initialize() != SQLITE_OK ||
	    sqlite3_open(argv[1], &db) != SQLITE_OK ||
	    sqlite3_exec(db, "CREATE TABLE t(x); INSERT INTO t VALUES (42);",
	        NULL, NULL, NULL) != SQLITE_OK)
		return 1;
	rec = sqlite3_recover_init(db, "main", argv[2]);
	if (rec == NULL || sqlite3_recover_run(rec) != SQLITE_OK ||
	    sqlite3_recover_finish(rec) != SQLITE_OK ||
	    sqlite3_open(argv[2], &recovered) != SQLITE_OK ||
	    sqlite3_prepare_v2(recovered, "SELECT x FROM t", -1, &stmt,
	        NULL) != SQLITE_OK || sqlite3_step(stmt) != SQLITE_ROW ||
	    sqlite3_column_int(stmt, 0) != 42)
		return 2;
	sqlite3_finalize(stmt);
	if (sqlite3_close(recovered) != SQLITE_OK || sqlite3_close(db) != SQLITE_OK)
		return 3;
	printf("PASS: SQLite %s recovered the selected row\n", sqlite3_libversion());
	return 0;
}
