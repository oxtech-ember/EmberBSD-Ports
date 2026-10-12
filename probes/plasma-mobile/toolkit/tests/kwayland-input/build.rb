#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), cross-build the installed Wayland consumer.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'Usage: build.rb CROSS_TOOLS SYSROOT WAYLAND_SCANNER NEW_WORK [UPSTREAM_SOURCE ORIGINAL_PKGSRC_PATCH]' unless [4, 6].include?(ARGV.length)
tools, sysroot, scanner = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[3])
abort 'NEW_WORK must be new and absolute' unless ARGV[3].start_with?('/') && !File.exist?(work)
Dir.mkdir(work)
owner = File.dirname(File.realpath(__FILE__))
prefix = sysroot + '/usr/pkg'
xml = prefix + '/share/plasma-wayland-protocols/fake-input.xml'
run = lambda do |name, *command|
  output, status = Open3.capture2e(*command)
  File.write("#{work}/#{name}.log", output)
  abort "#{name} failed; see saved log" unless status.success?
  output
end
ENV['PKG_CONFIG_SYSROOT_DIR'] = sysroot
ENV['PKG_CONFIG_LIBDIR'] = "#{prefix}/lib/pkgconfig:#{prefix}/qt6/lib/pkgconfig"
ENV['PKG_CONFIG_PATH'] = ''
pkgconfig = ENV.fetch('PKG_CONFIG', 'pkg-config')
flags = Shellwords.split(run.call('pkgconfig', pkgconfig, '--cflags', '--libs', 'KWaylandClient', 'wayland-client', 'wayland-server'))
%w[client-header server-header private-code].zip(%w[client.h server.h protocol.c]).each do |mode, suffix|
  run.call(mode, scanner, mode, xml, "#{work}/fake-input-#{suffix}")
end
common = ["--sysroot=#{sysroot}", "-B#{prefix}/gcc16/lib/gcc/aarch64--netbsd/16.2.0/", "-I#{prefix}/include", "-I#{work}", '-O2', '-Wall', '-Wextra', '-Werror', '-pthread']
run.call('protocol', "#{tools}/bin/aarch64--netbsd-gcc", *common, '-c', "#{work}/fake-input-protocol.c", '-o', "#{work}/protocol.o")
run.call('consumer', "#{tools}/bin/aarch64--netbsd-g++", *common, '-std=c++20', "#{owner}/main.cpp", "#{work}/protocol.o", *flags,
  "-L#{prefix}/gcc16/lib", "-Wl,-rpath-link,#{prefix}/lib", "-Wl,-rpath-link,#{prefix}/qt6/lib",
  '-Wl,-rpath,/usr/pkg/lib:/usr/pkg/qt6/lib:/usr/pkg/gcc16/lib', '-o', "#{work}/kwayland-input")
if ARGV.length == 6
  source, patch = ARGV.last(2).map { |p| File.realpath(p) }
  old = work + '/original'
  FileUtils.mkdir_p(old + '/src/client')
  FileUtils.cp(source + '/src/client/fakeinput.cpp', old + '/src/client')
  out, result = Open3.capture2e('patch', '-f', '-F', '0', '-p0', '-d', old, '-i', patch)
  File.write(work + '/original-patch.log', out)
  abort 'Original pkgsrc patch did not apply without fuzz' unless result.success?
  FileUtils.cp(work + '/fake-input-client.h', work + '/wayland-fake-input-client-protocol.h')
  negative = old + '/src/client/fakeinput.cpp'
  run.call('original-consumer', "#{tools}/bin/aarch64--netbsd-g++", *common, '-std=c++20',
    '-DKWaylandClient_EXPORTS', "-I#{source}/src/client", "-I#{source}/_KDE_build/src/client/KWaylandClient_autogen/include", "#{owner}/main.cpp", negative, "#{work}/protocol.o", *flags,
    "-L#{prefix}/gcc16/lib", "-Wl,-rpath-link,#{prefix}/lib", "-Wl,-rpath-link,#{prefix}/qt6/lib",
    '-Wl,-rpath,/usr/pkg/lib:/usr/pkg/qt6/lib:/usr/pkg/gcc16/lib', '-o', "#{work}/original-kwayland-input")
  %w[original current].each do |variant|
    file = variant == 'original' ? negative : source + '/src/client/fakeinput.cpp'
    expanded = run.call("preprocess-#{variant}", "#{tools}/bin/aarch64--netbsd-g++", *common,
      '-DKWaylandClient_EXPORTS', "-I#{source}/src/client", "-I#{source}/_KDE_build/src/client/KWaylandClient_autogen/include", '-std=c++20', '-E', file,
      *flags.select { |flag| flag.start_with?('-I', '-D') })
    File.write("#{work}/#{variant}.ii", expanded)
  end
  File.write(work + '/regression-inputs.sha256', [source + '/src/client/fakeinput.cpp', patch, negative,
    work + '/original-kwayland-input'].map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
end
inputs = [__FILE__, "#{owner}/main.cpp", xml, scanner, "#{work}/kwayland-input", "#{prefix}/lib/libKWaylandClient.so.6.7.5"]
File.write("#{work}/inputs-output.sha256", inputs.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: KWayland wire consumer cross-built; execute on the target with the matching installed package'
