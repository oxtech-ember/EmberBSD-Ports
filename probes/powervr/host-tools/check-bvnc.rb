#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Run from a configured, patched Mesa build. Keep every artifact in OUT.
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'usage: check-bvnc.rb MESA_SOURCE MESA_BUILD PCO_CLC COMMON_SPV OUT' unless ARGV.size == 5
mesa, build, pco, spv, out = ARGV.map { |v| File.expand_path(v) }
FileUtils.mkdir_p(out)
source = File.read(mesa + '/src/imagination/pco/uscgen/pco_clc.c')
parser = source[/static bool parse_bvnc\(.*?\n\}\n/m] or abort 'actual parser not found'
File.write(out + '/bvnc-parser.inc', parser)
FileUtils.cp(File.join(__dir__, 'bvnc-contract.c'), out)
db = JSON.parse(File.read(build + '/compile_commands.json'))
e = db.find { |v| v['file'].end_with?('/pvr_device_info.c') } or abort 'compile entry missing'
args = e['arguments'] || Shellwords.split(e.fetch('command'))
args = args.dup.reject { |v| v == '-MD' || v == '-c' }
%w[-MQ -MF -o].each { |key| while (i = args.index(key)); args.slice!(i, 2); end }
args.pop
args += ['-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
         '-I' + mesa + '/src/imagination/common', out + '/bvnc-contract.c',
         mesa + '/src/imagination/common/pvr_device_info.c', '-o', out + '/bvnc-contract']
File.write(out + '/compile.command', Shellwords.join(args) + "\n")
Dir.chdir(e['directory']) { abort 'contract compile failed' unless system(*args) }
abort 'contract failed' unless system(out + '/bvnc-contract')
checks = 0
run = lambda do |label, devices, valid|
  dir = out + '/' + label
  FileUtils.mkdir_p(dir)
  h = dir + '/programs.h'
  c = dir + '/programs.c'
  command = [pco, spv, h, c, *devices]
  File.write(dir + '/command', Shellwords.join(command) + "\n")
  unless valid
    File.write(h, "header sentinel\n")
    File.write(c, "source sentinel\n")
  end
  stdout, stderr, status = Open3.capture3({'PCO_DEBUG' => 'no_pred_cf'}, *command)
  File.write(dir + '/stdout', stdout)
  File.write(dir + '/stderr', stderr)
  File.write(dir + '/exit', status.exitstatus.to_s + "\n")
  if valid
    abort "#{label}: failed #{status.inspect}" unless status.success? && File.size?(h) && File.size?(c)
  else
    abort "#{label}: wrong status #{status.inspect}" unless status.exitstatus == 1
    abort "#{label}: changed outputs" unless File.read(h) == "header sentinel\n" && File.read(c) == "source sentinel\n"
    File.unlink(h, c)
    _, _, second = Open3.capture3({'PCO_DEBUG' => 'no_pred_cf'}, *command)
    abort "#{label}: created outputs" unless second.exitstatus == 1 && !File.exist?(h) && !File.exist?(c)
  end
  checks += 1
end
run.call('common', [], true)
run.call('old-name', ['BXM-4-64'], true)
run.call('exact', ['bvnc=36.56.104.183'], true)
run.call('leading-zero', ['bvnc=00036.00056.00104.00183'], true)
run.call('two-distinct', ['BXM-4-64', 'bvnc=36.56.104.183'], true)
invalid = ['', 'bvnc=', 'bvnc=1', 'bvnc=1.2', 'bvnc=1.2.3', 'bvnc=1.2.3.',
           'bvnc=.1.2.3', 'bvnc=1..2.3', 'bvnc=1.2..3', 'bvnc=-36.56.104.183',
           'bvnc=+36.56.104.183', 'bvnc= 36.56.104.183', 'bvnc=36.56.104.183 ',
           'bvnc=36.56.104.183x', 'bvnc=36.56.104.183.0', 'bvnc=65536.56.104.183',
           'bvnc=36.65536.104.183', 'bvnc=36.56.65536.183', 'bvnc=36.56.104.65536',
           'bvnc=4294967296.56.104.183', 'bvnc=36.56.104.' + '9' * 100,
           'bvnc=36.56.104.184', 'bvnc=0.0.0.0', 'bvnc=65535.65535.65535.65535',
           'not-a-device', 'common', 'BXM-4-64;false']
invalid.each_with_index { |v, i| run.call("bad-#{i}", [v], false) }
run.call('later-bad', ['bvnc=36.56.104.183', 'not-a-device'], false)
run.call('duplicate', ['bvnc=36.56.104.183', 'bvnc=36.56.104.183'], false)
run.call('duplicate-canonical', ['bvnc=36.56.104.183', 'bvnc=00036.00056.00104.00183'], false)
run.call('duplicate-alias', ['BXM-4-64', 'bvnc=36.52.104.182'], false)
run.call('duplicate-name-case', ['BXM-4-64', 'bxm-4-64'], false)
abort 'noncanonical identifier' unless File.read(out + '/exact/programs.c').include?('bvnc_36_56_104_183')
abort 'leading zero identifier differs' unless File.read(out + '/leading-zero/programs.c').include?('bvnc_36_56_104_183')
puts "PASS #{checks} actual CLI cases; rejected arguments preserve existing outputs and create no files"
