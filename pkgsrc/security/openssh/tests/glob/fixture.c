#include "includes.h"
#include "openbsd-compat/glob.h"
#include <stdlib.h>
#include <string.h>

int
main(void)
{
	glob_t result = {0};

	if (glob("*.txt", 0, NULL, &result) != 0 || result.gl_pathc != 2 ||
	    strcmp(result.gl_pathv[0], "a.txt") != 0 ||
	    strcmp(result.gl_pathv[1], "b.txt") != 0)
		abort();
	globfree(&result);
	memset(&result, 0, sizeof(result));
	if (glob("{a,b}.txt", GLOB_BRACE, NULL, &result) != 0 ||
	    result.gl_pathc != 2)
		abort();
	globfree(&result);
	return 0;
}
