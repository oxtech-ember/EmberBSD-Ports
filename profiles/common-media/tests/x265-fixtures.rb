#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Deterministic frame and independent decode checks.
require 'open3'
abort 'Usage: x265-fixtures.rb prepare NEW_FIXTURES | verify RESULTS FIXTURES' unless [2, 3].include?(ARGV.size)
mode, directory, fixtures = ARGV
case mode
when 'prepare'
  abort 'Unexpected argument' unless ARGV.size == 2
  Dir.mkdir(directory)
  frames = 4.times.map do |frame|
    y = Array.new(64 * 64) { |i| (i % 64 * 3 + i / 64 * 5 + frame * 37) % 256 }
    u = Array.new(32 * 32) { |i| (i % 32 * 7 + frame * 19) % 256 }
    v = Array.new(32 * 32) { |i| (i / 32 * 11 + frame * 23) % 256 }
    (y + u + v).pack('C*')
  end.join
  File.binwrite(File.join(directory, 'frames.yuv'), frames)
  puts "PASS: #{frames.bytesize} deterministic YUV420 bytes in four changing frames"
when 'verify'
  abort 'Missing fixtures' unless ARGV.size == 3
  ffmpeg = ENV.fetch('FFMPEG', 'ffmpeg')
  original = File.binread(File.join(fixtures, 'frames.yuv'))
  out, status = Open3.capture2e(ffmpeg, '-version')
  abort 'Cannot run independent decoder' unless status.success?
  File.write(File.join(directory, 'decoder-version.txt'), out)
  %w[neon scalar].each do |name|
    output = File.join(directory, "#{name}-decoded.yuv")
    abort "Output exists: #{output}" if File.exist?(output)
    out, status = Open3.capture2e(ffmpeg, '-nostdin', '-v', 'error', '-i',
      File.join(directory, "#{name}.hevc"), '-pix_fmt', 'yuv420p', '-f', 'rawvideo', output)
    File.write(File.join(directory, "#{name}-decode.log"), out)
    abort "Decoder failed: #{name}" unless status.success?
    abort "Decoded pixels differ: #{name}" unless File.binread(output) == original
    puts "PASS: independent #{name} HEVC decoding matches all #{original.bytesize} source bytes"
  end
else
  abort 'Expected prepare or verify'
end
