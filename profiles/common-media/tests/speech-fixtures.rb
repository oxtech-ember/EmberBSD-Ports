#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Validate results retrieved from the target.
require_relative 'lame-fixtures'

def speech_wave(path)
  data = File.binread(path)
  check(data.start_with?('RIFF') && data.byteslice(8, 4) == 'WAVE', 'Not WAVE')
  check(data.byteslice(4, 4).unpack1('V') == data.bytesize - 8, 'Wrong RIFF size')
  chunks = {}
  at = 12
  while at + 8 <= data.bytesize
    name = data.byteslice(at, 4)
    size = data.byteslice(at + 4, 4).unpack1('V')
    check(at + 8 + size <= data.bytesize, 'Truncated WAV chunk')
    chunks[name] = data.byteslice(at + 8, size)
    at += 8 + size + size % 2
  end
  check(chunks.key?('fmt ') && chunks.key?('data'), 'Missing WAVE chunks')
  format, channels, rate, _, _, bits = chunks['fmt '].unpack('vvVVvv')
  check([format, channels, rate, bits] == [1, 1, 22050, 16], 'Wrong speech PCM format')
  samples = chunks['data'].unpack('s<*')
  check(samples.size.between?(11025, 220500), 'Speech duration outside 0.5–10 seconds')
  check(samples.sum { |x| x*x } / samples.size > 10000, 'Speech has no signal')
  samples
end

check(ARGV.size == 2, 'Usage: speech-fixtures.rb RESULTS SONIC_INPUT_WAV')
directory, input = ARGV
normal = wav(File.join(directory, 'sonic-normal.wav'))
fast = wav(File.join(directory, 'sonic-fast.wav'))
original = wav(input)
check(normal == original, 'Sonic speed 1 changed the input')
check((fast.size * 2.0 / original.size - 1).abs < 0.02, 'Sonic speed 2 duration mismatch')
crossings = fast.each_cons(2).count { |a, b| a <= 0 && b > 0 }
frequency = crossings * 44100.0 / fast.size
check(frequency.between?(420, 460), 'Sonic changed pitch')
puts "PASS: Sonic CLI exact speed 1, #{fast.size} speed 2 samples, #{frequency.round(2)} Hz"
%w[en ru].each do |language|
  first = speech_wave(File.join(directory, 'espeak-results-r1', "#{language}-1.wav"))
  second = speech_wave(File.join(directory, 'espeak-results-r1', "#{language}-2.wav"))
  check(first == second, 'Repeated eSpeak process changed PCM')
  puts "PASS: eSpeak #{language}, #{first.size} exact repeated PCM samples"
end
