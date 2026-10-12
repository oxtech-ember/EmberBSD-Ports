#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Host-side fixture generation and byte checks.
require 'fileutils'

def check(ok, message)
  abort message unless ok
end

def wav(path)
  data = File.binread(path)
  check(data.start_with?('RIFF') && data.byteslice(8, 4) == 'WAVE', 'Not a RIFF/WAVE file')
  chunks = {}
  at = 12
  while at + 8 <= data.bytesize
    name = data.byteslice(at, 4)
    size = data.byteslice(at + 4, 4).unpack1('V')
    check(at + 8 + size <= data.bytesize, 'Truncated WAV chunk')
    chunks[name] = data.byteslice(at + 8, size)
    at += 8 + size + (size % 2)
  end
  check(chunks.key?('fmt ') && chunks.key?('data'), 'Missing WAV chunks')
  format, channels, rate, _, _, bits = chunks['fmt '].unpack('vvVVvv')
  check([format, channels, rate, bits] == [1, 1, 44100, 16], 'Unexpected PCM format')
  chunks['data'].unpack('s<*')
end

def tags(path)
  data = File.binread(path)
  check(data.start_with?("ID3".b) && [3, 4].include?(data.getbyte(3)) && data.getbyte(4).zero? && data.getbyte(5).zero?, 'Unexpected ID3 version/flags')
  limit = 10 + data.byteslice(6, 4).bytes.reduce(0) { |n, b| (n << 7) | b }
  check(limit <= data.bytesize, 'Truncated ID3 tag')
  at = 10
  result = {}
  while at + 10 <= limit && data.getbyte(at) != 0
    id = data.byteslice(at, 4)
    size_bytes = data.byteslice(at + 4, 4)
    size = data.getbyte(3) == 4 ? size_bytes.bytes.reduce(0) { |n, b| (n << 7) | b } : size_bytes.unpack1('N')
    check(size > 0 && at + 10 + size <= limit, 'Truncated ID3 frame')
    body = data.byteslice(at + 10, size)
    encoding = {0 => 'ISO-8859-1', 1 => 'UTF-16', 3 => 'UTF-8'}[body.getbyte(0)]
    if id.start_with?('T') || id == 'COMM'
      check(encoding, 'Unsupported text encoding')
      text = body.byteslice(id == 'COMM' ? 4 : 1, size)
      if id == 'COMM'
        if encoding == 'UTF-16'
          # Empty description may carry a BOM; its terminator is aligned.
          ending = (0...text.bytesize).step(2).find { |i| text.byteslice(i, 2) == "\0\0" }
          check(ending, 'Missing comment description terminator')
          text = text.byteslice(ending + 2, text.bytesize)
        else
          text = text.split("\0", 2).fetch(1)
        end
      end
      result[id] = text.force_encoding(encoding).encode('UTF-8').delete_suffix("\0")
    end
    at += 10 + size
  end
  result
end

if $PROGRAM_NAME == __FILE__
  mode, directory, fixture = ARGV
  case mode
  when 'prepare'
    check(ARGV.size == 2 && !File.exist?(directory), 'Usage: lame-fixtures.rb prepare NEW_FIXTURES')
    Dir.mkdir(directory)
    samples = Array.new(44100) { |i| (10000 * Math.sin(2 * Math::PI * 440 * i / 44100)).round }
    pcm = samples.pack('s<*')
    wave = 'RIFF'.b + [36 + pcm.bytesize].pack('V') + 'WAVEfmt '.b + [16, 1, 1, 44100, 88200, 2, 16].pack('VvvVVvv') + 'data'.b + [pcm.bytesize].pack('V') + pcm
    File.binwrite(File.join(directory, 'tone.wav'), wave)
    puts 'PASS: generated one second of deterministic mono PCM'
  when 'verify'
    check(ARGV.size == 3, 'Usage: lame-fixtures.rb verify TARGET_RESULTS FIXTURES')
    original = wav(File.join(fixture, 'tone.wav'))
    %w[utf8 utf16].each do |encoding|
      actual = tags(File.join(directory, "#{encoding}.mp3"))
      expected = {'TIT2'=>'Title café 東京', 'TPE1'=>'Artist café 東京', 'TALB'=>'Album café 東京',
                  'COMM'=>'Comment café 東京', 'TIT3'=>'Subtitle café 東京', 'TRCK'=>'7', 'TYER'=>'2026', 'TCON'=>'Speech'}
      expected.each { |key, text| check(actual[key] == text, "#{encoding}/#{key}: #{actual[key].inspect} != #{text.inspect}") }
      decoded = wav(File.join(directory, "#{encoding}.wav"))
      check(decoded.size == original.size, 'Decoded sample count differs')
      signal = original.sum { |n| n * n }.to_f
      noise = original.zip(decoded).sum { |a, b| (a - b)**2 }.to_f
      snr = 10 * Math.log10(signal / [noise, 1].max)
      check(snr >= 20, "Decoded signal mismatch: #{snr} dB")
      puts "PASS: #{encoding}, all eight metadata fields, #{decoded.size} samples, #{format('%.2f', snr)} dB SNR"
    end
  else
    abort 'Expected prepare or verify'
  end
end
