# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Host validation of exported Whisper JSON.
require 'json'

abort 'Usage: check-whisper-transcript.rb PREFIX MODEL_PATH JFK_WAV' unless ARGV.length == 3
prefix, model, wav = ARGV
expected = 'and so my fellow americans ask not what your country can do for you ask what you can do for your country'
normalize = ->(text) { text.downcase.gsub(/[^a-z]+/, ' ').strip }
wave = File.binread(wav)
abort 'Not a RIFF WAVE file' unless wave[0, 4] == 'RIFF' && wave[8, 4] == 'WAVE'
offset = 12
format = nil
data_bytes = nil
while offset + 8 <= wave.bytesize
  id = wave[offset, 4]
  size = wave[offset + 4, 4].unpack1('V')
  abort 'Truncated WAV chunk' if offset + 8 + size > wave.bytesize
  format = wave[offset + 8, 16].unpack('vvVVvv') if id == 'fmt ' && size >= 16
  data_bytes = size if id == 'data'
  offset += 8 + size + size % 2
end
abort 'Expected mono 16 kHz, 16-bit PCM' unless format && format[0] == 1 && format[1] == 1 && format[2] == 16_000 && format[4] == 2 && format[5] == 16 && data_bytes
duration_ms = data_bytes * 1000.0 / format[3]
document = JSON.parse(File.read("#{prefix}.json"))
abort 'Wrong tiny model' unless document.fetch('model').fetch('type') == 'tiny' && document.fetch('model').fetch('multilingual') == true
abort 'Wrong model identity' unless document.fetch('params').fetch('model') == model
abort 'Wrong language' unless document.fetch('params').fetch('language') == 'en' && document.fetch('result').fetch('language') == 'en'
segments = document.fetch('transcription')
abort 'Empty transcription' unless segments.is_a?(Array) && !segments.empty?
text = segments.map { |segment| segment.fetch('text') }.join(' ')
abort 'JSON words differ from independent reference' unless normalize.call(text) == expected
abort 'TXT words differ from reference' unless normalize.call(File.read("#{prefix}.txt")) == expected
previous = 0
segments.each do |segment|
  from, to = segment.fetch('offsets').values_at('from', 'to')
  abort 'Invalid segment bounds' unless from.is_a?(Integer) && to.is_a?(Integer) && from >= previous && to > from && to <= duration_ms + 10
  %w[from to].each do |key|
    time = segment.fetch('timestamps').fetch(key)
    match = /\A(\d{2}):(\d{2}):(\d{2}),(\d{3})\z/.match(time)
    abort 'Invalid timestamp syntax' unless match
    h, m, s, ms = match.captures.map(&:to_i)
    abort 'Timestamp and offset disagree' unless m < 60 && s < 60 && ((h * 60 + m) * 60 + s) * 1000 + ms == segment.fetch('offsets').fetch(key)
  end
  tokens = segment.fetch('tokens')
  abort 'Token details missing' unless tokens.is_a?(Array) && !tokens.empty?
  tokens.each do |token|
    probability = token.fetch('p')
    abort 'Invalid token probability' unless probability.is_a?(Numeric) && probability.finite? && probability.between?(0, 1)
    abort 'Invalid token ID' unless token.fetch('id').is_a?(Integer) && token.fetch('id') >= 0
  end
  previous = to
end
puts "PASS: exact independent JFK words, #{segments.length} JSON segments, bounded millisecond timestamps and token probabilities"
