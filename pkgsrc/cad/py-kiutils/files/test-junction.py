# SPDX-License-Identifier: BSD-2-Clause
"""Junction appearance survives parsing and serialization in either field order."""

import unittest

from kiutils.items.schitems import Junction
from kiutils.utils.sexpr import parse_sexp


class JunctionRoundTrip(unittest.TestCase):
    def test_diameter_and_color(self):
        for diameter in (0, 0.4, 1.27):
            for color_first in (False, True):
                with self.subTest(diameter=diameter, color_first=color_first):
                    fields = [['diameter', diameter], ['color', 10, 20, 30, 0.5]]
                    if color_first:
                        fields.reverse()
                    original = Junction.from_sexpr([
                        'junction', ['at', 12.7, 25.4], *fields,
                        ['uuid', 'bc6fe61c-647a-41cd-bf14-726d66f0c55f'],
                    ])
                    restored = Junction.from_sexpr(parse_sexp(original.to_sexpr()))
                    for junction in (original, restored):
                        self.assertEqual(junction.diameter, diameter)
                        self.assertEqual(
                            (junction.color.R, junction.color.G, junction.color.B, junction.color.A),
                            (10, 20, 30, 0.5))
                        self.assertEqual((junction.position.X, junction.position.Y), (12.7, 25.4))
                        self.assertEqual(junction.uuid, 'bc6fe61c-647a-41cd-bf14-726d66f0c55f')


if __name__ == '__main__':
    unittest.main()
