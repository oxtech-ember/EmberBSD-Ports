#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), unchanged upstream test binary staging.
require 'digest'
require 'fileutils'
require 'open3'
abort 'Usage: stage-gstreamer-tests.rb BUILT_SOURCE SYSROOT NEW_BUNDLE' unless ARGV.size == 3
source, sysroot = ARGV.first(2).map { |p| File.realpath(p) }
bundle = File.expand_path(ARGV[2])
abort 'NEW_BUNDLE must be absent and absolute' unless ARGV[2].start_with?('/') && !File.exist?(bundle)
readelf = ENV.fetch('READELF')
FileUtils.mkdir_p(bundle+'/bin')
FileUtils.mkdir_p(bundle+'/source')
%w[gstbuffer gstcaps gstevent gstquery gstsegment gststructure].each do |name|
  exe = source+'/output/tests/check/gst_'+name
  data, status = Open3.capture2e(readelf, '-h', '-d', exe)
  abort 'not a target test linked to the shared core' unless status.success? && data.include?('AArch64') && data.match?(/NEEDED.*\[libgstreamer-1.0.so.0\]/)
  abort 'test binary contains a build loader path' if data.match?(/(?:RPATH|RUNPATH).*\[(?:[^\]]*)(?:Volumes|private\/tmp|Users)/)
  FileUtils.cp(exe,bundle+'/bin/gst_'+name)
  FileUtils.cp(source+'/tests/check/gst/'+name+'.c',bundle+'/source/'+name+'.c')
end
FileUtils.cp(source+'/tests/check/meson.build',bundle+'/source/meson.build')
FileUtils.cp(__dir__+'/gstreamer-runtime.sh',bundle+'/gstreamer-runtime.sh')
libraries = %w[gstreamer check base controller net].map { |n| n == 'gstreamer' ? 'libgstreamer-1.0.so.0' : "libgst#{n}-1.0.so.0" }
File.write(bundle+'/runtime.sha256', libraries.map { |n| "#{Digest::SHA256.file(sysroot+'/usr/pkg/lib/'+n).hexdigest}  /usr/pkg/lib/#{n}\n" }.join)
files = Dir.glob(bundle+'/**/*').select { |p| File.file?(p) }.sort
File.write(bundle+'/files.sha256', files.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(bundle+'/')}\n" }.join)
puts 'Staged six unchanged upstream test suites; execution requires the same installed core package'
