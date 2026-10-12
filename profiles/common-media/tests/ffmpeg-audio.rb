#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Verify actual decoded PCM, not only exit status.
require_relative 'lame-fixtures'
check(ARGV.size == 2, 'Usage: ffmpeg-audio.rb RESULTS AUDIO_FIXTURES')
results, fixtures = ARGV
original = wav(File.join(fixtures, 'tone.wav'))
signal = original.sum { |n| n * n }.to_f
%w[audio opus].each do |name|
  decoded = wav(File.join(results, "#{name}.wav"))
  check(decoded.size == original.size, "#{name}: decoded sample count differs")
  noise = original.zip(decoded).sum { |a, b| (a - b)**2 }.to_f
  snr = 10 * Math.log10(signal / [noise, 1].max)
  check(snr >= 20, "#{name}: decoded signal differs (#{snr} dB)")
  puts "PASS: #{name}, #{decoded.size} samples, #{format('%.2f', snr)} dB SNR"
end
