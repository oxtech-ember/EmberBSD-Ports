/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). ICU target runtime acceptance. */
#include <unicode/ucol.h>
#include <unicode/uclean.h>

#include <unicode/ures.h>
#include <unicode/ustring.h>
int
main(int argc, char **argv)
{
	const UChar input[] = { 0x61, 0xe9, 0xd83c, 0xdf1f };
	const UChar expected[] = { 0x41, 0xc9, 0xd83c, 0xdf1f };
	UChar output[8];
	UErrorCode error = U_ZERO_ERROR;
	UCollator *collator;
	UResourceBundle *bundle, *answer;
	int32_t length;
	int result = 0;

	if (argc != 2)
		return 64;
	length = u_strToUpper(output, 8, input, 4, "en_US", &error);
	if (U_FAILURE(error) || length != 4 || u_memcmp(output, expected, 4) != 0)
		return 1;
	collator = ucol_open("en_US", &error);
	if (U_FAILURE(error) || collator == NULL)
		return 2;
	if (ucol_strcollUTF8(collator, "apple", -1, "pear", -1,
	    &error) != UCOL_LESS || U_FAILURE(error))
		result = 3;
	ucol_close(collator);
	if (result != 0)
		return result;
	error = U_ZERO_ERROR;
	bundle = ures_open(argv[1], "en", &error);
	if (U_FAILURE(error) || bundle == NULL)
		return 5;
	answer = ures_getByKey(bundle, "answer", NULL, &error);
	if (U_FAILURE(error) || answer == NULL)
		result = 6;
	else if (ures_getInt(answer, &error) != 42 || U_FAILURE(error))
		result = 7;
	ures_close(answer);
	ures_close(bundle);
	u_cleanup();
	return result;
}
