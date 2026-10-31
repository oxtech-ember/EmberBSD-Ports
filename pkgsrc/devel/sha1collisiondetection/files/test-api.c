#include <stddef.h>
#include <sha1dc/sha1.h>
#include <stdio.h>
#include <string.h>

static int
check(int safe, const char *message, size_t size, const unsigned char expected[20])
{
	SHA1_CTX ctx;
	unsigned char digest[20];

	SHA1DCInit(&ctx);
	SHA1DCSetSafeHash(&ctx, safe);
	SHA1DCUpdate(&ctx, message, size / 2);
	SHA1DCUpdate(&ctx, message + size / 2, size - size / 2);
	return SHA1DCFinal(digest, &ctx) == 0 &&
	    memcmp(digest, expected, sizeof(digest)) == 0;
}

static int
check_collision(const char *path, int safe, const unsigned char expected[20])
{
	SHA1_CTX ctx;
	unsigned char digest[20];
	char buffer[4096];
	size_t n;
	FILE *f;

	f = fopen(path, "rb");
	if (f == NULL)
		return 0;
	SHA1DCInit(&ctx);
	if (safe >= 0)
		SHA1DCSetSafeHash(&ctx, safe);
	do {
		n = fread(buffer, 1, sizeof(buffer), f);
		if (n != 0)
			SHA1DCUpdate(&ctx, buffer, n);
	} while (n == sizeof(buffer));
	if (ferror(f)) {
		fclose(f);
		return 0;
	}
	if (fclose(f) != 0)
		return 0;
	return SHA1DCFinal(digest, &ctx) == 1 &&
	    memcmp(digest, expected, sizeof(digest)) == 0;
}

int
main(int argc, char **argv)
{
	static const unsigned char empty[] = {
		0xda, 0x39, 0xa3, 0xee, 0x5e, 0x6b, 0x4b, 0x0d, 0x32, 0x55,
		0xbf, 0xef, 0x95, 0x60, 0x18, 0x90, 0xaf, 0xd8, 0x07, 0x09
	};
	static const unsigned char abc[] = {
		0xa9, 0x99, 0x3e, 0x36, 0x47, 0x06, 0x81, 0x6a, 0xba, 0x3e,
		0x25, 0x71, 0x78, 0x50, 0xc2, 0x6c, 0x9c, 0xd0, 0xd8, 0x9d
	};
	/* Upstream test/shattered-1.pdf and its safe-hash output. */
	static const unsigned char collision[] = {
		0x38, 0x76, 0x2c, 0xf7, 0xf5, 0x59, 0x34, 0xb3, 0x4d, 0x17,
		0x9a, 0xe6, 0xa4, 0xc8, 0x0c, 0xad, 0xcc, 0xbb, 0x7f, 0x0a
	};
	static const unsigned char safe_collision[] = {
		0x16, 0xe9, 0x6b, 0x70, 0x00, 0x0d, 0xd1, 0xe7, 0xc8, 0x5b,
		0x83, 0x68, 0xee, 0x19, 0x77, 0x54, 0x40, 0x0e, 0x58, 0xec
	};

	if (!check(0, "", 0, empty) || !check(1, "", 0, empty) ||
	    !check(0, "abc", 3, abc) || !check(1, "abc", 3, abc)) {
		fputs("SHA1DC vector failed\n", stderr);
		return 1;
	}
	if (argc != 2 || !check_collision(argv[1], 0, collision) ||
	    !check_collision(argv[1], 1, safe_collision) ||
	    !check_collision(argv[1], -1, safe_collision)) {
		fputs("SHA1DC collision vector failed\n", stderr);
		return 1;
	}
	return 0;
}
