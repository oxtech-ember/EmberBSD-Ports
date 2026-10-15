#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors (AI-assisted).
# Real occupied RTCP bind through the installed FFmpeg C API consumer.
require 'digest'
require 'json'
require 'open3'
require 'socket'

unless (ARGV.length == 4 || (ARGV.length == 5 && ARGV[4] == '--expect-leak')) &&
    ARGV[3].match?(/\A[0-9]+\z/) && Integer(ARGV[3], 10).between?(10000, 65000)
  abort 'Usage: ffmpeg-rtp-open.rb RECEIVER FF_LIBDIR NEW_OUT PORT [--expect-leak]'
end
receiver, library, out = ARGV.take(3).map { |p| File.expand_path(p) }
port = Integer(ARGV[3], 10)
before = ARGV.length == 5
Dir.mkdir(out)
sdp = File.join(out, 'stream.sdp')
File.write(sdp, "v=0\no=- 0 0 IN IP4 127.0.0.1\ns=E35 occupied RTCP control\n" \
  "c=IN IP4 127.0.0.1\nt=0 0\nm=video #{port} RTP/AVP 96\na=rtpmap:96 H265/90000\n")
log = File.join(out, 'memcheck.log')
command = ['valgrind', '--tool=memcheck', '--leak-check=full', '--show-leak-kinds=all',
  '--errors-for-leak-kinds=all', '--track-origins=yes', '--error-exitcode=99',
  '--log-file=' + log, receiver, sdp, File.join(out, 'decoded.i420'),
  File.join(out, 'frames.csv'), File.join(out, 'report.json'), '700', '200',
  File.join(out, 'ready')]
env = {'LD_LIBRARY_PATH' => [library, ENV['LD_LIBRARY_PATH']].compact.join(':')}
File.write(File.join(out, 'command.json'), JSON.pretty_generate({arguments: command,
  environment: env, expect_before_leak: before, library: library,
  library_files: Dir.glob(File.join(library, 'libavformat.so*')).map do |path|
    {path: path, sha256: Digest::SHA256.file(path).hexdigest}
  end}) + "\n")
held = UDPSocket.new
begin
  held.bind('127.0.0.1', port + 1)
  stdout, stderr, status = Open3.capture3(env, *command)
  File.write(File.join(out, 'stdout.log'), stdout)
  File.write(File.join(out, 'stderr.log'), stderr)
ensure
  held.close
end
value = JSON.parse(File.read(File.join(out, 'report.json')))
raise 'No-input failure was accepted' unless value['ok'] == false && value['frames'] == 0
memory = File.read(log)
if before
  raise 'Expected causal partial-open leak was not reproduced' unless status.exitstatus == 99 &&
    memory.include?('definitely lost: 187 bytes in 1 blocks') &&
    memory.include?('indirectly lost: 66,357 bytes in 2 blocks') &&
    memory.include?('ERROR SUMMARY: 3 errors from 3 contexts (suppressed: 0 from 0)') &&
    memory.include?('rtp_open')
else
  raise 'Fixed open/close failure or memory regression' unless status.exitstatus == 1 &&
    memory.include?('in use at exit: 0 bytes in 0 blocks') &&
    memory.include?('ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 0 from 0)')
end
[port, port + 1].each do |number|
  socket = UDPSocket.new
  begin
    socket.bind('127.0.0.1', number)
  ensure
    socket.close
  end
end
result = {ok: true, expected_before_leak: before, child_exit: status.exitstatus,
          ports_released: true, receiver_report: value}
File.write(File.join(out, 'result.json'), JSON.pretty_generate(result) + "\n")
puts JSON.generate(result)
