/* SPDX-License-Identifier: MIT */
/* EmberBSD installed-library contract. AI-assisted; not an upstream test. */
#include <sys/types.h>
#include <sys/wait.h>

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <sqlite3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static pid_t child = -1;

static void
interrupted(int signo)
{

	if (child > 0)
		(void)kill(child, SIGKILL);
	_exit(128 + signo);
}

static void
cleanup(void)
{

	if (child > 0) {
		(void)kill(child, SIGKILL);
		(void)waitpid(child, NULL, 0);
	}
}

static void
fail(const char *message)
{

	fprintf(stderr, "FAIL: %s\n", message);
	exit(EXIT_FAILURE);
}

static void
exec_sql(sqlite3 *db, const char *sql)
{

	if (sqlite3_exec(db, sql, NULL, NULL, NULL) != SQLITE_OK)
		fail(sqlite3_errmsg(db));
}

static sqlite3 *
open_db(const char *path)
{
	sqlite3 *db = NULL;

	if (sqlite3_open(path, &db) != SQLITE_OK)
		fail(db ? sqlite3_errmsg(db) : "open");
	sqlite3_busy_timeout(db, 2000);
	return db;
}

static void
expect(sqlite3 *db, const char *sql, const char *expected)
{
	sqlite3_stmt *stmt = NULL;
	const unsigned char *value;

	if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK ||
	    sqlite3_step(stmt) != SQLITE_ROW)
		fail(sqlite3_errmsg(db));
	value = sqlite3_column_text(stmt, 0);
	if (value == NULL || strcmp((const char *)value, expected) != 0)
		fail(sql);
	if (sqlite3_step(stmt) != SQLITE_DONE || sqlite3_finalize(stmt) != SQLITE_OK)
		fail("statement completion");
}

int
main(int argc, char **argv)
{
	sqlite3 *db, *reader;
	sqlite3_stmt *stmt = NULL;
	int fd, pipefd[2], status;
	char ready;
	const char *payload = "quote ' ; DROP TABLE facts; --";

	if (argc != 2) {
		fprintf(stderr, "Usage: consumer NEW_DATABASE\n");
		return 2;
	}
	atexit(cleanup);
	/* A bounded run, including the child/pipe handshake. */
	signal(SIGALRM, interrupted);
	signal(SIGINT, interrupted);
	signal(SIGTERM, interrupted);
	alarm(20);
	fd = open(argv[1], O_WRONLY | O_CREAT | O_EXCL, 0600);
	if (fd == -1 || close(fd) != 0)
		fail("database path already exists or cannot be created");
	db = open_db(argv[1]);
	printf("headers=%s runtime=%s source=%s threadsafe=%d\n",
	    SQLITE_VERSION, sqlite3_libversion(), sqlite3_sourceid(),
	    sqlite3_threadsafe());
	if (strcmp(SQLITE_VERSION, sqlite3_libversion()) != 0 ||
	    strcmp(SQLITE_SOURCE_ID, sqlite3_sourceid()) != 0)
		fail("header/runtime source mismatch");
	if (sqlite3_threadsafe() != 1)
		fail("serialized thread-safe library required");
	expect(db, "PRAGMA journal_mode=WAL", "wal");
	exec_sql(db, "PRAGMA synchronous=FULL; CREATE TABLE facts(id INTEGER PRIMARY KEY, value TEXT);"
	    "INSERT INTO facts VALUES(1,'committed');"
	    "CREATE VIRTUAL TABLE search USING fts5(body);");
	if (sqlite3_prepare_v2(db, "INSERT INTO facts VALUES(2,?)", -1,
	    &stmt, NULL) != SQLITE_OK || sqlite3_bind_text(stmt, 1, payload,
	    -1, SQLITE_STATIC) != SQLITE_OK || sqlite3_step(stmt) != SQLITE_DONE ||
	    sqlite3_finalize(stmt) != SQLITE_OK)
		fail("prepared parameter binding");
	expect(db, "SELECT value FROM facts WHERE id=2", payload);
	exec_sql(db, "INSERT INTO search VALUES('The amber pump interval is seven days.');");
	expect(db, "SELECT count(*) FROM search WHERE search MATCH 'pump'", "1");
	expect(db, "SELECT count(*) FROM search WHERE search MATCH 'nonexistent'", "0");
	expect(db, "SELECT json_extract('{\"interval\":7}', '$.interval')", "7");
	if (sqlite3_exec(db, "SELECT json_extract('broken', '$')", NULL, NULL, NULL) == SQLITE_OK ||
	    sqlite3_exec(db, "SELECT * FROM search WHERE search MATCH '\"'", NULL, NULL, NULL) == SQLITE_OK)
		fail("malformed JSON/FTS input accepted");
	exec_sql(db, "BEGIN; UPDATE facts SET value='rolled back' WHERE id=1; ROLLBACK;");
	expect(db, "SELECT value FROM facts WHERE id=1", "committed");
	reader = open_db(argv[1]);
	exec_sql(reader, "BEGIN");
	expect(reader, "SELECT value FROM facts WHERE id=1", "committed");
	exec_sql(db, "BEGIN IMMEDIATE; UPDATE facts SET value='new commit' WHERE id=1; COMMIT;");
	expect(reader, "SELECT value FROM facts WHERE id=1", "committed");
	exec_sql(reader, "COMMIT");
	expect(reader, "SELECT value FROM facts WHERE id=1", "new commit");
	if (sqlite3_close(reader) != SQLITE_OK || sqlite3_close(db) != SQLITE_OK)
		fail("close before fork");
	/* Fork with no open SQLite connections. Kill only our own writer. */
	if (pipe(pipefd) != 0 || (child = fork()) == -1)
		fail("pipe/fork");
	if (child == 0) {
		child = -1;
		close(pipefd[0]);
		db = open_db(argv[1]);
		exec_sql(db, "PRAGMA synchronous=FULL; PRAGMA cache_size=4; BEGIN IMMEDIATE;"
		    "UPDATE facts SET value='must disappear' WHERE id=1;"
		    "INSERT INTO facts VALUES(3,zeroblob(262144));");
		if (write(pipefd[1], "R", 1) != 1)
			_exit(1);
		for (;;)
			pause();
	}
	close(pipefd[1]);
	if (read(pipefd[0], &ready, 1) != 1 || ready != 'R')
		fail("writer did not reach uncommitted transaction");
	close(pipefd[0]);
	db = open_db(argv[1]);
	expect(db, "SELECT value FROM facts WHERE id=1", "new commit");
	expect(db, "SELECT count(*) FROM facts", "2");
	if (sqlite3_close(db) != SQLITE_OK)
		fail("concurrent reader close");
	if (kill(child, SIGKILL) != 0 || waitpid(child, &status, 0) != child ||
	    !WIFSIGNALED(status) || WTERMSIG(status) != SIGKILL)
		fail("writer crash");
	child = -1;
	db = open_db(argv[1]);
	expect(db, "SELECT value FROM facts WHERE id=1", "new commit");
	expect(db, "SELECT count(*) FROM facts", "2");
	expect(db, "PRAGMA integrity_check", "ok");
	if (sqlite3_close(db) != SQLITE_OK)
		fail("final close");
	if (sqlite3_shutdown() != SQLITE_OK)
		fail("final SQLite shutdown");
	alarm(0);
	puts("PASS: bindings FTS5 JSON rollback WAL snapshots concurrent reader SIGKILL/reopen integrity");
	return 0;
}
