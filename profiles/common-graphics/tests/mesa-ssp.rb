#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual Mesa TU with NetBSD fortified headers.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: mesa-ssp.rb MESA_26_2_5_ARCHIVE PKGSRC_MESA_BUILD NEW_WORK' unless ARGV.length == 3
archive, build = ARGV.first(2).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
abort 'unexpected Mesa archive' unless Digest::SHA256.file(archive).hexdigest == 'bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9'
Dir.mkdir(work)
relative = 'src/gallium/auxiliary/vl/vl_csc.c'
commands = "#{build}/compile_commands.json"
entry = JSON.parse(File.read(commands)).find { |item| item['file'].end_with?(relative) }
abort 'missing real Mesa compile command' unless entry
source = File.expand_path(entry['file'], entry['directory'])
original, status = Open3.capture2('tar', '-xOf', archive, "mesa-26.2.6/#{relative}")
abort 'archive member extraction failed' unless status.success?
File.write("#{work}/original.c", original)
FileUtils.mkdir_p(File.dirname("#{work}/patched/#{relative}"))
File.write("#{work}/patched/#{relative}", original)
patch = File.expand_path('../../../pkgsrc/graphics/MesaLib/patches/patch-src_gallium_auxiliary_vl_vl__csc.c', __dir__)
out, status = Open3.capture2e('patch', '-f', '-N', '-F', '0', '-p0', '-d', "#{work}/patched", stdin_data: File.read(patch))
File.write("#{work}/patch.log", out)
abort 'patch did not apply exactly' unless status.success? && !out.match?(/offset|fuzz/i)
fixed = "#{work}/patched/#{relative}"
abort 'configured source differs from canonical patched archive' unless File.read(source) == File.read(fixed)
args = Shellwords.split(entry.fetch('command'))
wrapper_dir = "#{File.dirname(File.dirname(build))}/.cwrapper/bin"
compiler = "#{wrapper_dir}/#{File.basename(args.shift)}"
abort 'missing actual pkgsrc compiler wrapper' unless File.executable?(compiler)
abort 'unexpected source argument' unless args.last == entry['file']
args.pop
args += ['-iquote', File.dirname(source)]
config = "#{File.dirname(wrapper_dir)}/config"
abort 'missing actual pkgsrc SSP configuration' unless File.read("#{config}/cc").include?('prepend=-D_FORTIFY_SOURCE=2')
env = { 'PATH' => "#{wrapper_dir}:#{ENV.fetch('PATH')}", 'CWRAPPERS_CONFIG_DIR' => config }
%w[original patched].each do |kind|
  command = args.dup
  { '-o' => "#{work}/#{kind}.o", '-MF' => "#{work}/#{kind}.d" }.each do |flag, value|
    index = command.index(flag)
    abort "missing #{flag}" unless index
    command[index + 1] = value
  end
  input = kind == 'original' ? "#{work}/original.c" : fixed
  File.write("#{work}/#{kind}-command.txt", Shellwords.join([compiler, *command, input]) + "\n")
  out, status = Open3.capture2e(env, compiler, *command, input, chdir: entry['directory'])
  File.write("#{work}/#{kind}.log", out)
  if kind == 'original'
    abort 'original TU did not reproduce the fortified memcpy macro failure' unless !status.success? && out.match?(/macro.*memcpy.*passed 15 arguments/)
    puts 'PASS: original upstream TU fails on the real fortified NetBSD memcpy macro'
  else
    abort 'canonical patched TU failed to compile as target ELF' unless status.success? && File.binread("#{work}/patched.o", 4) == "\x7fELF"
    # Keep the same command's includes and wrapper-defined SSP settings.
    command[command.index('-c')] = '-E'
    command += ['-dM']
    command[command.index('-o') + 1] = "#{work}/macros.txt"
    out, status = Open3.capture2e(env, compiler, *command, input, chdir: entry['directory'])
    File.write("#{work}/preprocess.log", out)
    macros = File.read("#{work}/macros.txt")
    abort 'SSP was disabled or the memcpy macro was bypassed' unless status.success? && macros.include?('#define _FORTIFY_SOURCE 2') && macros.match?(/^#define memcpy\(/)
    puts 'PASS: patched actual TU is ELF and retains _FORTIFY_SOURCE=2 plus the memcpy macro'
  end
end
File.write("#{work}/inputs.sha256", [archive, commands, patch, source, compiler, "#{config}/cc"].map { |path| "#{Digest::SHA256.file(path).hexdigest}  #{path}\n" }.join)
