/* SPDX-License-Identifier: BSD-2-Clause */
/* Exercise the production checks without running a privileged executable. */
#include "darwin-defaults.c"

int
main(int argc, char **argv)
{
	uuid_t root_user;

	if (argc != 3 || mbr_uid_to_uuid(0, root_user) != 0)
		return 2;
	if (strcmp(argv[1], "acl") == 0)
		check_acl(argv[2], root_user, EXISTING);
	else if (strcmp(argv[1], "new-file") == 0)
		check_acl(argv[2], root_user, NEW_FILE);
	else if (strcmp(argv[1], "new-directory") == 0)
		check_acl(argv[2], root_user, NEW_DIRECTORY);
	else if (strcmp(argv[1], "new-subtree") == 0)
		check_acl(argv[2], root_user, NEW_SUBTREE);
	else if (strcmp(argv[1], "optional") == 0)
		check_trusted_path(argv[2], root_user, NEW_FILE, 0);
	else if (strcmp(argv[1], "required") == 0)
		check_trusted_path(argv[2], root_user, EXISTING, 0);
	else
		return 2;
	return 0;
}
