/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Actual common SQLite RBU API regression. */
#include <sqlite3.h>
#include "sqlite3rbu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void
require(int ok, const char *message)
{
	if (!ok) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(1);
	}
}

static void
sql(const char *path, const char *text)
{
	sqlite3 *db = NULL;
	char *error = NULL;

	require(sqlite3_open(path, &db) == SQLITE_OK, "open fixture");
	if (sqlite3_exec(db, text, NULL, NULL, &error) != SQLITE_OK) {
		fprintf(stderr, "%s\n", error);
		sqlite3_free(error);
		(void)sqlite3_close(db);
		require(0, "fixture SQL");
	}
	require(sqlite3_close(db) == SQLITE_OK, "close fixture");
}

static void
expect(const char *path, const char *query, const char *wanted)
{
	sqlite3 *db = NULL;
	sqlite3_stmt *stmt = NULL;
	const unsigned char *actual;

	require(sqlite3_open(path, &db) == SQLITE_OK, "open result");
	require(sqlite3_prepare_v2(db, query, -1, &stmt, NULL) == SQLITE_OK,
	    "prepare result");
	require(sqlite3_step(stmt) == SQLITE_ROW, "read result");
	actual = sqlite3_column_text(stmt, 0);
	require(actual != NULL && strcmp((const char *)actual, wanted) == 0,
	    query);
	require(sqlite3_finalize(stmt) == SQLITE_OK, "finalize result");
	require(sqlite3_close(db) == SQLITE_OK, "close result");
}

int
main(void)
{
	sqlite3rbu *rbu;
	char *error = NULL;
	int rc, steps;

	require(sqlite3_compileoption_used("ENABLE_RBU") == 1, "ENABLE_RBU");
	sql("target.db", "CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT);"
	    "INSERT INTO t VALUES(1,'old'),(2,'delete');");
	sql("update.db", "CREATE TABLE data_t(id, v, rbu_control);"
	    "INSERT INTO data_t VALUES(1,'new','.x'),(2,NULL,1),(3,'insert',0);");
	rbu = sqlite3rbu_open("target.db", "update.db", NULL);
	require(rbu != NULL, "open update");
	require(sqlite3rbu_step(rbu) == SQLITE_OK, "first update step");
	require(sqlite3rbu_progress(rbu) > 0, "update made progress");
	require(sqlite3rbu_close(rbu, &error) == SQLITE_OK && error == NULL,
	    "suspend update");
	expect("target.db", "SELECT group_concat(v,',') FROM (SELECT v FROM t ORDER BY id)",
	    "old,delete");
	rbu = sqlite3rbu_open("target.db", "update.db", NULL);
	require(rbu != NULL, "resume update");
	for (steps = 0; steps < 100; steps++) {
		rc = sqlite3rbu_step(rbu);
		if (rc != SQLITE_OK)
			break;
	}
	require(rc == SQLITE_DONE, "finish resumed update");
	require(sqlite3rbu_close(rbu, &error) == SQLITE_DONE && error == NULL,
	    "close completed update");
	expect("target.db", "SELECT group_concat(v,',') FROM (SELECT v FROM t ORDER BY id)",
	    "new,insert");
	expect("target.db", "PRAGMA integrity_check", "ok");
	sql("invalid.db", "CREATE TABLE data_t(id, v, rbu_control);"
	    "INSERT INTO data_t VALUES(4,'invalid','?');");
	rbu = sqlite3rbu_open("target.db", "invalid.db", NULL);
	require(rbu != NULL, "open invalid update");
	for (steps = 0; steps < 100; steps++) {
		rc = sqlite3rbu_step(rbu);
		if (rc != SQLITE_OK)
			break;
	}
	require(rc == SQLITE_ERROR, "reject malformed rbu_control");
	require(sqlite3rbu_close(rbu, &error) == SQLITE_ERROR && error != NULL,
	    "report invalid update");
	sqlite3_free(error);
	expect("target.db", "SELECT group_concat(v,',') FROM (SELECT v FROM t ORDER BY id)",
	    "new,insert");
	puts("PASS: RBU insert/update/delete, suspend/resume, invalid control");
	return 0;
}
