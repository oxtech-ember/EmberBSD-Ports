/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Link only FreeType; run once with a sibling HarfBuzz and once without it. */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <ft2build.h>
#include FT_FREETYPE_H

int
main(int argc, char **argv)
{
	FT_Library library;
	FT_Face face;
	int expected;

	if (argc != 3 || (strcmp(argv[1], "present") != 0 &&
	    strcmp(argv[1], "absent") != 0))
		return 1;
	expected = strcmp(argv[1], "present") == 0;
	if (dlsym(RTLD_DEFAULT, "hb_version_atleast") != NULL)
		return 2;
	if (FT_Init_FreeType(&library) || FT_New_Face(library, argv[2], 0, &face) ||
	    FT_Set_Pixel_Sizes(face, 0, 18) ||
	    FT_Load_Char(face, 'a', FT_LOAD_FORCE_AUTOHINT | FT_LOAD_RENDER))
		return 3;
	if ((dlsym(RTLD_DEFAULT, "hb_version_atleast") != NULL) != expected)
		return 4;
	FT_Done_Face(face);
	FT_Done_FreeType(library);
	puts(expected ? "PASS: loaded sibling HarfBuzz" :
	    "PASS: rendering without optional HarfBuzz");
	return 0;
}
