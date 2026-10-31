#include "test-xdiff-compat.h"
#include "xdiff.h"

#ifdef NDEBUG
#error "xdiff regression requires assertions"
#endif
#ifdef NDEBUG
#error "test-xdiff-runtime requires assertions"
#endif

union allocation {
	max_align_t align;
	struct { size_t size; unsigned long magic; } data;
};
static const unsigned long magic = 0x51a42c23UL;
static size_t attempts, fail_at, live;

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
	printf("xdiff custom allocator: %zu failure points passed\n", total);
	return 0;
}
