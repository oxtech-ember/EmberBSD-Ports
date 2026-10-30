#include <libpsl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int check(const psl_ctx_t *text, const psl_ctx_t *binary, const char *name, size_t len)
{
	int a = psl_lookup_rule(text, name, len);
	int b = psl_lookup_rule(binary, name, len);
	if (a != b) {
		fprintf(stderr, "rule mismatch: %.*s (%d != %d)\n", (int)len, name, a, b);
		return 1;
	}
	return 0;
}

int main(int argc, char **argv)
{
	psl_ctx_t *text, *binary;
	char bad[] = { 'c', 'o', 'm', 0, 'x' };
	char long_name[128];
	int failed = 0;

	if (argc < 4 || !(text = psl_load_file(argv[1])) ||
	    !(binary = psl_load_file(argv[2])))
		return 2;
	for (int i = 3; i < argc; ++i)
		failed |= check(text, binary, argv[i], strlen(argv[i]));
	failed |= check(text, binary, "com.extra", 3);
	failed |= psl_lookup_rule(text, "com.extra", 3) != PSL_RULE_ICANN;
	failed |= psl_lookup_rule(text, "ck", 2) != (PSL_RULE_ICANN | PSL_RULE_WILDCARD);
	failed |= psl_lookup_rule(text, "www.ck", 6) != (PSL_RULE_ICANN | PSL_RULE_EXCEPTION);
	failed |= psl_lookup_rule(text, "blogspot.com", 12) != PSL_RULE_PRIVATE;
	failed |= psl_lookup_rule(text, "not-a-rule.invalid", 18) != -1;
	failed |= check(text, binary, "ck", 2);
	failed |= check(text, binary, "www.ck", 6);
	failed |= check(text, binary, "blogspot.com", 12);
	failed |= check(text, binary, "not-a-rule.invalid", 18);
	memset(long_name, 'a', sizeof(long_name));
	failed |= psl_lookup_rule(text, long_name, sizeof(long_name)) != -1;
	failed |= psl_lookup_rule(binary, long_name, sizeof(long_name)) != -1;
	failed |= psl_lookup_rule(text, bad, sizeof(bad)) != -1;
	failed |= psl_lookup_rule(binary, bad, sizeof(bad)) != -1;
	failed |= psl_lookup_rule(text, "", 0) != -1;
	failed |= psl_lookup_rule(binary, "", 0) != -1;
	failed |= psl_lookup_rule(NULL, "com", 3) != -1;
	failed |= psl_lookup_rule(text, NULL, 1) != -1;
	failed |= psl_lookup_rule(binary, "x", (size_t)PTRDIFF_MAX + 1) != -1;
	psl_free(text);
	psl_free(binary);
	return failed ? 1 : 0;
}
