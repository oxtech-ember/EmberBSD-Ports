#include "test-xdiff-compat.h"
#include "xdiff.h"

#ifdef NDEBUG
#error "test-xdiff-runtime requires assertions"
#endif

union allocation {
	max_align_t align;
	struct { size_t size; unsigned long magic; } data;
};
static const unsigned long magic = 0x51a42c23UL;
static size_t attempts, fail_at, live;
static int bugs;

void
test_report_bug(void)
{
	bugs++;
}

static int
line_cb(void *payload, mmbuffer_t *line, int count)
{
	(void)payload; (void)line; (void)count;
	return 0;
}

static int
hunk_cb(long a, long b, long c, long d, void *payload)
{
	(void)a; (void)b; (void)c; (void)d; (void)payload;
	return 0;
}

static void
check_invalid_context(void)
{
	char old[] = "old\n", new[] = "new\n";
	mmfile_t a = { old, sizeof(old) - 1 }, b = { new, sizeof(new) - 1 };
	xpparam_t options = { 0 };
	xdemitcb_t cb = { 0 };
	xdemitconf_t config = { 0 };
	cb.out_line = line_cb;
	config.ctxlen = -1;
	bugs = 0;
	assert(xdl_diff(&a, &b, &options, &config, &cb) == -1);
	assert(bugs == 1 && live == 0);
	config.hunk_func = hunk_cb;
	bugs = 0;
	assert(xdl_diff(&a, &b, &options, &config, &cb) == -1);
	assert(bugs == 1 && live == 0);
	config.ctxlen = 0;
	config.interhunkctxlen = -1;
	bugs = 0;
	assert(xdl_diff(&a, &b, &options, &config, &cb) == -1);
	assert(bugs == 1 && live == 0);
	config.hunk_func = 0;
	bugs = 0;
	assert(xdl_diff(&a, &b, &options, &config, &cb) == -1);
	assert(bugs == 1 && live == 0);
}

void *
test_alloc(size_t size)
{
	union allocation *p;
	if (++attempts == fail_at || size > SIZE_MAX - sizeof(*p))
		return NULL;
	p = malloc(sizeof(*p) + size);
	if (p == NULL)
		return NULL;
	p->data.size = size;
	p->data.magic = magic;
	live++;
	return p + 1;
}

void *
test_calloc(size_t count, size_t size)
{
	void *p;
	if (size && count > SIZE_MAX / size)
		return NULL;
	p = test_alloc(count * size);
	if (p != NULL)
		memset(p, 0, count * size);
	return p;
}

void
test_free(void *ptr)
{
	union allocation *p;
	if (ptr == NULL)
		return;
	p = (union allocation *)ptr - 1;
	assert(p->data.magic == magic && live > 0);
	p->data.magic = 0;
	live--;
	free(p);
}

void *
test_realloc(void *ptr, size_t size)
{
	union allocation *old;
	void *p;
	if (ptr == NULL)
		return test_alloc(size);
	old = (union allocation *)ptr - 1;
	assert(old->data.magic == magic);
	p = test_alloc(size);
	if (p != NULL) {
		memcpy(p, ptr, old->data.size < size ? old->data.size : size);
		test_free(ptr);
	}
	return p;
}

static int
merge(void)
{
	char original[] = "alpha\nbeta\ngamma\n";
	char left[] = "alpha\nleft\ngamma\n";
	char right[] = "alpha\nright\ngamma\n";
	static const char expected[] =
	    "alpha\n<<<<<<<\nleft\n=======\nright\n>>>>>>>\ngamma\n";
	mmfile_t base = { original, sizeof(original) - 1 };
	mmfile_t a = { left, sizeof(left) - 1 };
	mmfile_t b = { right, sizeof(right) - 1 };
	xmparam_t options;
	mmbuffer_t result = { 0 };
	int status;
	memset(&options, 0, sizeof(options));
	options.xpp.flags = XDF_PATIENCE_DIFF | XDF_NEED_MINIMAL;
	status = xdl_merge(&base, &a, &b, &options, &result);
	if (status >= 0) {
		assert(status == 1);
		assert(result.size == sizeof(expected) - 1);
		assert(memcmp(result.ptr, expected, sizeof(expected) - 1) == 0);
	}
	test_free(result.ptr);
	assert(live == 0);
	return status;
}

static void
merge_deletions(void)
{
	char text[] = "base\n", empty[] = "";
	mmfile_t base = { text, sizeof(text) - 1 }, deleted = { empty, 0 };
	mmfile_t *left[] = { &deleted, &base, &deleted };
	mmfile_t *right[] = { &base, &deleted, &deleted };
	xmparam_t options = { 0 };
	mmbuffer_t result;
	size_t i;
	int status;

	options.level = XDL_MERGE_ZEALOUS;
	for (i = 0; i < 3; i++) {
		memset(&result, 0, sizeof(result));
		status = xdl_merge(&base, left[i], right[i], &options, &result);
		if (status != 0)
			fprintf(stderr, "delete case %lu status %d\n", (unsigned long)i, status);
		assert(status == 0);
		assert(result.size == 0);
		/* Both sides changed use the general merge, which allocates. */
		assert((result.ptr != NULL) == (i == 2 || XDL_MERGE_ALLOC_EMPTY));
		test_free(result.ptr);
		assert(live == 0);
	}
}

static void
merge_empty(void)
{
	char empty[] = "";
	char sentinel;
	mmfile_t file = { empty, 0 };
	xmparam_t options;
	mmbuffer_t result = { &sentinel, 0 };

	memset(&options, 0, sizeof(options));
	assert(xdl_merge(&file, &file, &file, &options, &result) == 0);
	assert(result.size == 0);
	assert((result.ptr != NULL) == XDL_MERGE_ALLOC_EMPTY);
	test_free(result.ptr);
	assert(live == 0);
}

int
main(void)
{
	size_t total, i;
	fail_at = SIZE_MAX;
	attempts = 0;
	assert(merge() == 1);
	total = attempts;
	assert(total > 0);
	for (i = 1; i <= total; i++) {
		attempts = 0;
		fail_at = i;
		assert(merge() < 0);
	}
	fail_at = SIZE_MAX;
	check_invalid_context();
	merge_empty();
	merge_deletions();
	printf("xdiff custom allocator: %lu failure points passed\n", (unsigned long)total);
	return 0;
}
