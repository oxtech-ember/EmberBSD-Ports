#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual generated D-Bus target-path regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: dbus-runtime-paths.rb PKGSRC CROSS_MAKECONF ORIGINAL_SOURCE FIXED_SOURCE NEW_WORK' unless ARGV.length == 5
tree, conf, original, source = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p("#{work}/fixture/output/bus")
make = ENV.fetch('BMAKE', 'bmake')
run = lambda do |name, *args|
  out, status = Open3.capture2e(make, '-C', "#{tree}/sysutils/dbus", "MAKECONF=#{conf}", *args)
  File.write("#{work}/#{name}.log", out)
  [out, status.success?]
end
args, ok = run.call('cross', 'show-var', 'VARNAME=MESON_ARGS')
abort 'cross recipe query failed' unless ok
%w[session_socket_dir test_socket_dir].each do |option|
  abort "missing target #{option}" unless Shellwords.split(args).include?("-D#{option}=/tmp")
end
native, ok = run.call('native', 'USE_CROSS_COMPILE=no', 'show-var', 'VARNAME=MESON_ARGS')
abort 'native recipe query failed' unless ok
abort 'native socket selection changed' if native.match?(/-D(?:session|test)_socket_dir=/)
puts 'GREEN: actual cross recipe pins target socket directories; native selection is unchanged'

files = %w[output/config.h output/bus/session.conf]
reset = lambda do |origin|
  files.each { |file| FileUtils.cp("#{origin}/#{file}", "#{work}/fixture/#{file}") }
end
check = lambda do |label|
  _, success = run.call(label, "WRKSRC=#{work}/fixture", 'emberbsd-dbus-runtime-paths')
  success
end
reset.call(original)
abort 'original fixture has no non-target session directory' if File.read("#{original}/output/config.h").include?('#define DBUS_SESSION_SOCKET_DIR "/tmp"')
abort 'original host-contaminated configuration accepted' if check.call('original-red')
puts 'RED: original generated configuration with the host temporary directory is rejected'
reset.call(source)
abort 'newly configured source rejected' unless check.call('fixed-green')
puts 'GREEN: actual freshly configured target header and session policy pass'

mutations = {
  'session-directory' => ['output/config.h', '#define DBUS_SESSION_SOCKET_DIR "/tmp"'],
  'test-directory' => ['output/config.h', '#define DBUS_TEST_SOCKET_DIR "/tmp"'],
  'test-listener' => ['output/config.h', '#define TEST_LISTEN "unix:tmpdir=/tmp"'],
  'session-listener' => ['output/bus/session.conf', '<listen>unix:tmpdir=/tmp</listen>']
}
mutations.each do |name, (file, needle)|
  reset.call(source)
  fixture = "#{work}/fixture/#{file}"
  body = File.read(fixture)
  abort "upstream changed #{name}" unless body.include?(needle)
  File.write(fixture, body.sub(needle, needle.sub('/tmp', '/host-only/socket-cache')))
  abort "host path accepted in #{name}" if check.call("reject-#{name}")
end
inputs = [__FILE__, conf, "#{tree}/sysutils/dbus/Makefile", "#{source}/meson.build"] +
  [original, source].flat_map { |root| files.map { |file| "#{root}/#{file}" } }
File.write("#{work}/inputs.sha256", inputs.map { |file| "#{Digest::SHA256.file(file).hexdigest}  #{file}\n" }.join)
puts 'PASS: every generated socket path rejects host contamination; target session execution is a separate check'
