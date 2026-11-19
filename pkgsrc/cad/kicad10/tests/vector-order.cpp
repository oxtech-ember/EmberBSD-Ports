// Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: GPL-3.0-or-later
// Target contract for ordered VECTOR2I containers with equal-radius points.
#include <math/vector2d_ordered.h>

int main()
{
    const VECTOR2I xy( 3, 4 );
    const VECTOR2I yx( 4, 3 );

    VECTOR2I_MAP<int> values;
    values[xy] = 31;
    values[yx] = 41;

    if( values.size() != 2 || values.find( xy ) == values.end()
            || values.find( yx ) == values.end() || values.at( xy ) != 31
            || values.at( yx ) != 41 )
        return 1;

    VECTOR2I_SET points;
    points.insert( xy );
    points.insert( yx );

    return points.size() == 2 && points.find( xy ) != points.end() && points.find( yx ) != points.end() ? 0 : 2;
}
