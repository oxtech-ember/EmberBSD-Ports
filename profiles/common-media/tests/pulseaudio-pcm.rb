#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exact PCM round trip through the null sink.
mode, fixture, capture = ARGV
case mode
when 'generate'
  abort 'Usage: pulseaudio-pcm.rb generate NEW_PCM' unless ARGV.size == 2
  samples = Array.new(12_000) { |i| ((i * 997) % 20_001) - 10_000 }
  File.open(fixture, File::WRONLY | File::CREAT | File::EXCL, 0600) { |f| f.write(([0] * 4800 + samples + [0] * 4800).pack('s<*')) }
when 'check'
  abort 'Usage: pulseaudio-pcm.rb check PCM CAPTURE' unless ARGV.size == 3
  source = File.binread(fixture)
  data = File.binread(capture)
  abort 'Wrong PCM fixture size' unless source.bytesize == 43_200
  offset = data.index(source)
  abort 'Captured stream does not contain the exact PCM fixture' unless offset && offset.even?
  puts "PASS: 12000 payload samples plus silence guards survived PulseAudio exactly; offset=#{offset / 2}, captured=#{data.bytesize / 2}"
else
  abort 'Expected generate or check'
end
