#include <ldap.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SUCCESS 0
#define FILTER_GROUP_PREFIX "(&(objectclass=posixGroup)"
#define FILTER_OR_PREFIX "(|"
#define FILTER_OR_SUFFIX ")"
#define FILTER_CN_PREFIX "(cn="
#define FILTER_CN_SUFFIX ")"

/* SOURCE FUNCTIONS */

int
main(void)
{
	char *group, *user, *filter;

	group = ldap_parse_groups("  engineering\t dev%ops ");
	user = ldap_escape_value("alice");
	assert(group != NULL && user != NULL);
	assert(asprintf(&filter, "%s(memberUid=%s))", group, user) > 0);
	assert(strcmp(filter, "(&(objectclass=posixGroup)(|(cn=engineering)"
	    "(cn=dev%ops))(memberUid=alice))") == 0);
	free(filter);
	free(group);
	ber_memfree(user);
	assert(ldap_parse_groups(NULL) == NULL);
	return 0;
}
