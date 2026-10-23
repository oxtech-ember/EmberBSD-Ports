#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual in-tree Pango transitive-link regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: pango-cross-link.rb PKGSRC CROSS_MAKECONF BUILT_SOURCE ORIGINAL_BUILD_LOG NEW_WORK' unless ARGV.length == 5
tree, conf, source, red_log = ARGV.first(4).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
make = ENV.fetch('BMAKE', 'bmake')
readelf = ENV.fetch('READELF', 'readelf')
recipe = File.expand_path('../../../pkgsrc/devel/pango', __dir__)
stock = File.expand_path('../../../upstream/pkgsrc/devel/pango', __dir__)
FileUtils.mkdir_p(work)
flag = "-Wl,-rpath-link,#{source}/output/pango"
wrkdir = File.dirname(source)
wrktop = File.expand_path('../../../..', source)
inputs = [__FILE__, conf, red_log, "#{source}/output/build.ninja"]

%w[original patched].each do |variant|
  root = "#{work}/#{variant}"
  FileUtils.mkdir_p("#{root}/devel")
  Dir.children(tree).each do |entry|
    next if entry == 'devel'
    FileUtils.ln_s("#{tree}/#{entry}", "#{root}/#{entry}")
  end
  Dir.children("#{tree}/devel").each do |entry|
    next if entry == 'pango'
    FileUtils.ln_s("#{tree}/devel/#{entry}", "#{root}/devel/#{entry}")
  end
  origin = variant == 'original' ? stock : recipe
  FileUtils.cp_r(origin, "#{root}/devel/pango")
  inputs << "#{origin}/Makefile"
end
query = lambda do |variant, native|
  out, status = Open3.capture2e(make, '-C', "#{work}/#{variant}/devel/pango",
    "MAKECONF=#{conf}", "WRKOBJDIR=#{wrktop}",
    *Array(native ? 'USE_CROSS_COMPILE=no' : nil), '-V', '${OPSYS}|${LDFLAGS}')
  File.write("#{work}/#{variant}-#{native ? 'native' : 'cross'}.log", out)
  abort 'recipe parsing failed' unless status.success?
  out.strip
end
original = query.call('original', false)
patched = query.call('patched', false)
abort 'unexpected cross target' unless original.start_with?('NetBSD|') && patched.start_with?('NetBSD|')
abort 'original already contains link-only search path' if original.include?('-rpath-link,')
abort 'corrected recipe does not supply exact build path' unless Shellwords.split(patched.split('|', 2).last).include?(flag)
abort 'native recipe changed' unless query.call('original', true) == query.call('patched', true)
puts 'GREEN: real recipe selects link-only path for NetBSD cross builds; native flags unchanged'

line = File.readlines(red_log).find { |l| l.start_with?('aarch64--netbsd-gcc  -o utils/pango-list ') }
abort 'missing original failed Pango command' unless line
args = Shellwords.split(line)
abort 'original command already contains correction' if args.any? { |a| a.include?('-rpath-link,') }
args[0] = "#{wrkdir}/.cwrapper/bin/aarch64--netbsd-gcc"
abort 'actual pkgsrc compiler wrapper missing' unless File.executable?(args[0])
output = "utils/pango-list-cross-link-#{Process.pid}"
args[args.index('-o') + 1] = output
inputs << args[0]
env = { 'CWRAPPERS_CONFIG_DIR' => "#{wrkdir}/.cwrapper/config",
        'LD_LIBRARY_PATH' => "#{source}/output/pango" }

%w[original patched].each do |variant|
  cmd = args.dup
  cmd << flag if variant == 'patched'
  File.write("#{work}/#{variant}.command", Shellwords.join(cmd) + "\n")
  out, status = Open3.capture2e(env, *cmd, chdir: "#{source}/output")
  File.write("#{work}/#{variant}.log", "exit=#{status.exitstatus}\n#{out}")
  if variant == 'original'
    abort 'original indirect-library failure did not reproduce' unless !status.success? &&
      out.include?('libpangoft2-1.0.so.0') && out.include?('not found')
    puts 'RED: real original command cannot resolve the in-tree libpangoft2 dependency'
  else
    abort 'corrected link failed' unless status.success?
    binary = "#{work}/pango-list"
    FileUtils.mv("#{source}/output/#{output}", binary)
    dynamic, inspected = Open3.capture2e(readelf, '-d', binary)
    File.write("#{work}/dynamic.log", dynamic)
    abort 'ELF dynamic metadata unavailable' unless inspected.success? && dynamic.include?('NEEDED')
    paths = dynamic.lines.select { |l| l.match?(/RPATH|RUNPATH/) }.join
    abort 'link-only path leaked into runtime metadata' if paths.include?("#{source}/output/pango")
    puts 'GREEN: one link-only flag resolves the dependency without adding its path to ELF runtime metadata'
    inputs << binary
  end
end
Dir.glob("#{source}/output/pango/*.so.*").select { |p| File.file?(p) && !File.symlink?(p) }.each { |p| inputs << p }
File.write("#{work}/inputs.sha256", inputs.uniq.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: causal actual-ELF link check; target text rendering remains separate acceptance'
