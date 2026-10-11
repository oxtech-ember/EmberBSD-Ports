/* SPDX-License-Identifier: MIT
 * Copyright (c) 2011-2014 Dmitry Matveev <me@dmitrymatveev.co.uk>
 * Copyright (c) 2014-2021 Vladimir Kondratyev <vladimir@kondratyev.su>
 * Copyright (c) 2026 EmberBSD contributors
 * Adapted from libinotify-kqueue 20240724 configure.ac (AI-assisted).
 * Run in a disposable directory on the target; syscall failures are not "no".
 */
#include <sys/types.h>
#include <sys/event.h>
#include <sys/stat.h>
#include <sys/time.h>

#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int
move_event(int fd, const char *from, const char *to)
{
	struct kevent ev;
	const struct timespec wait = { 1, 0 };
	int kq, result;

	kq = kqueue();
	if (kq == -1)
		err(2, "kqueue");
	EV_SET(&ev, fd, EVFILT_VNODE, EV_ADD | EV_ENABLE | EV_ONESHOT,
	    NOTE_WRITE | NOTE_EXTEND, 0, NULL);
	if (kevent(kq, &ev, 1, NULL, 0, &wait) == -1)
		err(2, "register vnode event");
	if (rename(from, to) == -1)
		err(2, "rename");
	if (kevent(kq, NULL, 0, &ev, 1, &wait) != 1 || (ev.flags & EV_ERROR))
		errx(2, "missing or failed vnode event");
	result = (ev.fflags & NOTE_EXTEND) != 0;
	if (close(kq) == -1)
		err(2, "close kqueue");
	return result;
}

int
main(void)
{
	char work[] = "inotify-features.XXXXXX";
	int dir, file, into, from, opath = 0, oempty = 0, atempty = 0;

	if (mkdtemp(work) == NULL || chdir(work) == -1 || mkdir("dir", 0700) == -1)
		err(2, "create isolated work directory");
	dir = open("dir", O_RDONLY | O_DIRECTORY);
	file = open("file", O_CREAT | O_EXCL | O_RDWR, 0600);
	if (dir == -1 || file == -1 || close(file) == -1)
		err(2, "create test file");
	into = move_event(dir, "file", "dir/file");
	from = move_event(dir, "dir/file", "file");
#ifdef O_PATH
	file = open("dir", O_PATH);
	if (file == -1 && errno != EINVAL && errno != EOPNOTSUPP)
		err(2, "open O_PATH");
	if (file != -1) {
		opath = lseek(file, 0, SEEK_SET) == -1;
		if (close(file) == -1)
			err(2, "close O_PATH");
	}
#endif
#ifdef O_EMPTY_PATH
	file = openat(dir, "", O_RDONLY | O_EMPTY_PATH);
	if (file == -1 && errno != EINVAL && errno != ENOENT && errno != EOPNOTSUPP)
		err(2, "openat O_EMPTY_PATH");
	if (file != -1) {
		oempty = 1;
		if (close(file) == -1)
			err(2, "close O_EMPTY_PATH");
	}
#endif
#if defined(AT_EMPTY_PATH) && defined(AT_EACCESS)
	atempty = faccessat(dir, "", R_OK, AT_EACCESS | AT_EMPTY_PATH) == 0;
	if (!atempty && errno != EINVAL && errno != ENOENT && errno != EOPNOTSUPP)
		err(2, "faccessat AT_EMPTY_PATH");
#endif
	if (close(dir) == -1 || unlink("file") == -1 || rmdir("dir") == -1 ||
	    chdir("..") == -1 || rmdir(work) == -1)
		err(2, "cleanup");
	printf("ember_cv_note_extend_to=%s\n", into ? "yes" : "no");
	printf("ember_cv_note_extend_from=%s\n", from ? "yes" : "no");
	printf("ember_cv_o_path=%s\n", opath ? "yes" : "no");
	printf("ember_cv_o_empty_path=%s\n", oempty ? "yes" : "no");
	printf("ember_cv_at_empty_path=%s\n", atempty ? "yes" : "no");
	return 0;
}
