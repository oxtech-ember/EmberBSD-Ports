/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Run against the installed libattr ABI. */
#include <sys/types.h>
#include <sys/xattr.h>
#include <attr/attributes.h>
#include <attr/libattr.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void
fail(const char *operation)
{
	perror(operation);
	exit(EXIT_FAILURE);
}

int
main(int argc, char **argv)
{
	char value[32];
	int source, destination;
	ssize_t length;

	if (argc != 3) {
		fprintf(stderr, "Usage: %s SOURCE DESTINATION\n", argv[0]);
		return EXIT_FAILURE;
	}
	source = open(argv[1], O_RDWR | O_CREAT | O_EXCL, 0600);
	if (source == -1)
		fail("create source");
	destination = open(argv[2], O_RDWR | O_CREAT | O_EXCL, 0600);
	if (destination == -1)
		fail("create destination");
	if (fsetxattr(source, "user.ember-abi", "first", 5, XATTR_CREATE) == -1) {
		if (errno == EOPNOTSUPP || errno == ENOSYS) {
			fprintf(stderr, "UNSUPPORTED: filesystem xattrs: %s\n", strerror(errno));
			close(source);
			close(destination);
			return 77;
		}
		fail("fsetxattr create");
	}
	if (setxattr(argv[1], "user.ember-abi", "first", 5, XATTR_CREATE) != -1 || errno != EEXIST)
		fail("setxattr duplicate CREATE");
	if (setxattr(argv[1], "user.ember-abi", "second", 6, XATTR_REPLACE) == -1)
		fail("setxattr REPLACE");
	if (attr_copy_file(argv[1], argv[2], NULL, NULL) == -1)
		fail("attr_copy_file");
	length = getxattr(argv[2], "user.ember-abi", value, sizeof(value));
	if (length != 6 || memcmp(value, "second", 6) != 0)
		fail("getxattr copied value");
	if (fsetxattr(source, "user.ember-abi", "third", 5, XATTR_REPLACE) == -1)
		fail("fsetxattr REPLACE");
	if (attr_copy_fd(argv[1], source, argv[2], destination, NULL, NULL) == -1)
		fail("attr_copy_fd");
	length = fgetxattr(destination, "user.ember-abi", value, sizeof(value));
	if (length != 5 || memcmp(value, "third", 5) != 0)
		fail("fgetxattr copied value");
	if (fremovexattr(destination, "user.ember-abi") == -1 ||
	    removexattr(argv[1], "user.ember-abi") == -1)
		fail("remove attributes");
	close(source);
	close(destination);
	puts("PASS: installed libattr API, file/fd copy and CREATE/REPLACE behavior");
	return EXIT_SUCCESS;
}
