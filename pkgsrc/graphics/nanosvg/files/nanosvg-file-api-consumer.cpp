/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include "nanosvg.h"

#include <cstdio>

int main()
{
    FILE* svg = std::tmpfile();
    if( !svg )
        return 1;

    static const char document[] =
            "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"8\">"
            "<rect width=\"10\" height=\"8\" fill=\"#336699\"/></svg>";

    if( std::fputs( document, svg ) < 0 )
    {
        std::fclose( svg );
        return 2;
    }

    std::rewind( svg );

    // nsvgParseFromFile owns and closes the FILE*.
    NSVGimage* image = nsvgParseFromFile( svg, "px", 96.0f );
    if( !image )
        return 3;

    const bool valid = image->width == 10.0f && image->height == 8.0f
                       && image->shapes != nullptr;
    nsvgDelete( image );
    return valid ? 0 : 4;
}
