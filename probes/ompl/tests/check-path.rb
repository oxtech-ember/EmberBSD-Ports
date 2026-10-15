#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Independent acceptance of exported CSV points.
require 'csv'
abort 'Usage: check-path.rb PATH_CSV' unless ARGV.length == 1
rows = CSV.read(ARGV.fetch(0))
abort 'Unexpected CSV header' unless rows.shift == %w[x y]
points = rows.map do |row|
  abort 'Expected two coordinates' unless row.length == 2
  row.map do |value|
    number = Float(value)
    abort 'Coordinate outside finite unit square' unless number.finite? && number.between?(0, 1)
    number
  end
end
abort 'Too few path states' unless points.length >= 3
[[points.first, [0.1, 0.5]], [points.last, [0.9, 0.5]]].each do |actual, expected|
  abort 'Wrong path endpoint' unless actual.zip(expected).all? { |a, b| (a - b).abs < 1e-12 }
end
rectangle = [[0.4, 0.15], [0.6, 0.15], [0.6, 0.85], [0.4, 0.85]]
def turn(a, b, c)
  (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
end
def on_segment(a, b, p)
  turn(a, b, p).abs < 1e-14 && 2.times.all? { |d| p[d].between?(*[a[d], b[d]].minmax) }
end
def intersects(a, b, c, d)
  values = [turn(a, b, c), turn(a, b, d), turn(c, d, a), turn(c, d, b)]
  (values[0] * values[1] < 0 && values[2] * values[3] < 0) ||
    on_segment(a, b, c) || on_segment(a, b, d) || on_segment(c, d, a) || on_segment(c, d, b)
end
length = 0.0
points.each do |point|
  abort 'Path state inside closed obstacle' if point[0].between?(0.4, 0.6) && point[1].between?(0.15, 0.85)
end
points.each_cons(2) do |a, b|
  rectangle.each_with_index do |c, i|
    abort 'Path edge touches or crosses obstacle' if intersects(a, b, c, rectangle[(i + 1) % 4])
  end
  length += Math.hypot(a[0] - b[0], a[1] - b[1])
end
abort 'Unexpected path length' unless length > 0.8 && length < 5
puts "PASS: #{points.length} CSV states, continuous collision-free edges, length=#{format('%.12f', length)}"
