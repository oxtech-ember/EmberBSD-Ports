#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors (AI-assisted).
# Build actual FFmpeg translation units; never replace their clock/parser logic.
require 'digest'
require 'json'
require 'open3'
require 'shellwords'

if ARGV.length < 6 || !(ARGV.drop(6) - %w[--baseline --build-only]).empty?
  abort 'Usage: ffmpeg-rtp-regressions.rb SOURCE BUILD PREFIX CHECKER RECEIVED.rtp NEW_OUT [--baseline] [--build-only]'
end
source, build, prefix, checker, capture, out = ARGV.take(6).map { |p| File.expand_path(p) }
baseline = ARGV.drop(6).include?('--baseline')
build_only = ARGV.drop(6).include?('--build-only')
Dir.mkdir(out)
tests = File.expand_path(__dir__)
config = File.readlines(File.join(build, 'ffbuild/config.mak')).filter_map do |line|
  line.chomp.split('=', 2) if line.match?(/\A(?:CC|CPPFLAGS|CFLAGS)=/)
end.to_h
patched = File.read(File.join(source, 'libavformat/rtpdec.h')).include?('base_timestamp_initialized')
raise 'Selected source does not match --baseline mode' if patched == baseline
compiler = Shellwords.split(config.fetch('CC'))
flags = ['-DHAVE_AV_CONFIG_H', *Shellwords.split(config.fetch('CPPFLAGS')),
         *Shellwords.split(config.fetch('CFLAGS'))]
base = compiler + flags + ['-ffunction-sections', '-fdata-sections', '-fvisibility=hidden',
  '-I' + build, '-I' + source, '-I' + File.join(source, 'libavformat')]
link = ['-Wl,--gc-sections', '-Wl,-rpath,/usr/pkg/lib/ffmpeg9:/usr/pkg/lib:/usr/pkg/gcc16/lib',
  '-L' + File.join(prefix, 'lib/ffmpeg9'), '-L' + File.join(prefix, 'lib'),
  '-lavformat', '-lavcodec', '-lavutil', '-lm']
commands = []
execute = lambda do |name, args, expected = 0, env = {}|
  commands << {name: name, directory: build, environment: env, arguments: args, expected_exit: expected}
  stdout, stderr, status = Open3.capture3(env, *args, chdir: build)
  File.write(File.join(out, name + '.stdout'), stdout)
  File.write(File.join(out, name + '.stderr'), stderr)
  File.write(File.join(out, 'commands.json'), JSON.pretty_generate(commands) + "\n")
  raise "#{name} exit #{status.exitstatus}, expected #{expected}: #{stderr}" unless status.exitstatus == expected
  stdout
end
# Extract only the exact unchanged upstream support function and its license.
utils_path = File.join(source, 'libavformat/utils.c')
utils = File.read(utils_path)
support = utils[/^uint64_t ff_parse_ntp_time\(uint64_t ntp_ts\)\n\{\n.*?^\}\n/m]
raise 'Upstream NTP support function shape changed' unless support
support_file = File.join(out, 'utils-clock-support.c')
File.write(support_file, utils.split('#include', 2).first + "#include \"libavformat/internal.h\"\n" + support)
File.write(File.join(out, 'support-extraction.json'), JSON.pretty_generate({source: utils_path,
  source_sha256: Digest::SHA256.hexdigest(utils), exact_function: support,
  function_sha256: Digest::SHA256.hexdigest(support)}) + "\n")
clock = File.join(out, 'rtp-clock')
clock_args = base + ['-DRTP_UNIT_SOURCE="' + File.join(source, 'libavformat/rtpdec.c') + '"',
  '-DRTP_INFO_SOURCE="' + File.join(source, 'libavformat/rtsp.c') + '"']
clock_args << '-DCLOCK_PATCHED=1' if patched
execute.call('build-clock', clock_args + [File.join(tests, 'ffmpeg-rtp-clock.c'),
  File.join(tests, 'ffmpeg-rtp-info.c'), support_file, *link, '-o', clock])
parser_object = File.join(out, 'parser.o')
execute.call('build-parser-source', base + ['-I' + File.join(source, 'libavcodec'),
  '-Dav_parser_init=unit_unused_parser_init', '-Dav_parser_close=unit_unused_parser_close',
  '-Dav_parser_parse2=unit_av_parser_parse2', '-Dff_fetch_timestamp=unit_ff_fetch_timestamp',
  '-c', File.join(source, 'libavcodec/parser.c'), '-o', parser_object])
parser = File.join(out, 'parser-position')
execute.call('build-parser-probe', compiler + flags.reject { |f| f == '-DHAVE_AV_CONFIG_H' } + ['-std=c11', '-Wall', '-Wextra',
  '-Wpedantic', '-Wconversion', '-Wshadow', '-Werror', '-isystem', File.join(prefix, 'include/ffmpeg9'),
  File.join(tests, 'ffmpeg-parser-position.c'), parser_object, *link, '-o', parser])
# Instrument an exact local copy of the independent Examples RFC7798 checker.
# Every inserted timestamp is the actually observed RTP header value.
text = File.read(checker)
replacements = {
  "nal_io = nil\nbegin\n" => "current_rtp_timestamp = nil\nnal_record_io = File.open(ENV.fetch('NAL_RECORDS'), 'wbx')\nat_exit { nal_record_io.close unless nal_record_io.closed? }\nnal_io = nil\nbegin\n",
  "    nal_digest.update(bytes)\n" => "    nal_digest.update(bytes)\n    nal_record_io.write([bytes.bytesize, current_rtp_timestamp].pack('Nq>') + bytes)\n",
  "    previous_marker = rtp[:marker]\n" => "    previous_marker = rtp[:marker]\n    current_rtp_timestamp = rtp[:timestamp]\n"
}
replacements.each do |before, after|
  raise 'Independent capture checker shape changed' unless text.scan(before).length == 1
  text = text.sub(before, after)
end
exporter = File.join(out, 'export-captured-nals.rb')
File.write(exporter, text)
records = File.join(out, 'observed-nals.bin')
execute.call('capture-check', ['ruby', exporter, capture, '--events', 'received',
  '--expect-pt', '96', '--clock-step', '9000'], 0, {'NAL_RECORDS' => records})
File.write(File.join(out, 'inputs.json'), JSON.pretty_generate({source: source, build: build,
  baseline: baseline, build_only: build_only, checker_sha256: Digest::SHA256.file(checker).hexdigest,
  capture_sha256: Digest::SHA256.file(capture).hexdigest,
  observed_nals_sha256: Digest::SHA256.file(records).hexdigest,
  source_inputs: [File.join(build, 'config.h'), File.join(build, 'ffbuild/config.mak'),
    *%w[libavformat/rtpdec.c libavformat/rtpdec.h libavformat/rtsp.c libavcodec/parser.c libavformat/utils.c].map { |f| File.join(source, f) },
    *%w[ffmpeg-rtp-clock.c ffmpeg-rtp-info.c ffmpeg-parser-position.c].map { |f| File.join(tests, f) }].map do |f|
      {path: f, sha256: Digest::SHA256.file(f).hexdigest}
    end}) + "\n")
unless build_only
  env = {'LD_LIBRARY_PATH' => [File.join(prefix, 'lib/ffmpeg9'), File.join(prefix, 'lib'),
                              '/usr/local/lib64'].join(':')}
  run = lambda do |name, binary, arguments, expected|
    log = File.join(out, name + '.memcheck')
    result = execute.call(name, ['valgrind', '--tool=memcheck', '--leak-check=full',
      '--show-leak-kinds=all', '--errors-for-leak-kinds=all', '--track-origins=yes',
      '--error-exitcode=99', '--log-file=' + log, binary, *arguments], expected, env)
    memory = File.read(log)
    raise "#{name} Memcheck failed" unless memory.include?('in use at exit: 0 bytes in 0 blocks') &&
      memory.include?('ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 0 from 0)')
    result
  end
  lines = run.call('clock', clock, [], baseline ? 1 : 0).lines.map { |l| JSON.parse(l) }
  raise 'Clock regression counts changed' unless lines.last ==
    {'checks' => baseline ? 44 : 52, 'failures' => baseline ? 17 : 0}
  [-1, 0].each do |position|
    result = JSON.parse(run.call('parser-pos' + position.to_s, parser, [records, position.to_s],
                                 baseline && position == -1 ? 1 : 0))
    raise 'Parser frame/metadata regression' unless result['frames'] == 40 &&
      result['output_positions'].all? { |p| p == position }
  end
end
puts JSON.generate({ok: true, baseline: baseline, build_only: build_only,
                    clock: clock, parser: parser, results: out})
