#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted actual Meson configuration regression.
require 'tmpdir'
require 'fileutils'
require 'open3'
abort 'Usage: iris-clc-configure.rb HOST_PYTHON MESON_PY MESA_SOURCE' unless ARGV.length == 3
python, meson, source = ARGV.map { |p| File.realpath(p) }
abort 'Expected pinned Mesa 26.2.5 source' unless File.read(source + '/VERSION').strip == '26.2.5'
upstream = File.read(source + '/meson.build')
start = upstream.index("if get_option('precomp-compiler') != 'system'") or abort 'Missing upstream generator selection'
finish = upstream.index('\nwith_llvm = with_llvm'.gsub('\\n', "\n"), start) or abort 'Missing upstream CLC boundary'
fragment = upstream[start...finish]
spirv = upstream[/with_spirv_tools = get_option\('spirv-tools'\).*?\n\n/m] or abort 'Missing upstream SPIRV-Tools feature check'
assigned = fragment.scan(/^([a-z][a-z0-9_]*)\s*=/).flatten
inputs = fragment.scan(/\bwith_[a-z0-9_]+\b/).uniq - assigned
Dir.mktmpdir('iris-clc-configure-', '/tmp') do |work|
  FileUtils.mkdir_p(work + '/bin')
  %w[mesa_clc vtn_bindgen2].each do |name|
    File.write(work + '/bin/' + name, "#!/bin/sh\nexit 99\n")
    File.chmod(0755, work + '/bin/' + name)
  end
  File.write(work + '/meson.options', <<~OPTIONS)
    option('mesa-clc', type: 'combo', choices: ['auto', 'enabled', 'system'], value: 'auto')
    option('precomp-compiler', type: 'combo', choices: ['auto', 'enabled', 'disabled', 'system'], value: 'auto')
    option('spirv-tools', type: 'feature', value: 'disabled')
  OPTIONS
  definitions = inputs.map { |name| name + ' = ' + (name == 'with_tools' ? '[]' : name == 'with_gallium_iris' ? 'true' : 'false') }.join("\n")
  File.write(work + '/meson.build', "project('iris-clc-configuration', meson_version: '>=1.12.1')\n" + definitions + "\n" + fragment + spirv)
  commands = [
    ['old-target-clc', %w[-Dmesa-clc=auto -Dprecomp-compiler=auto -Dspirv-tools=disabled], false],
    ['native-generators', %w[-Dmesa-clc=system -Dprecomp-compiler=system -Dspirv-tools=disabled], true]
  ]
  commands.each do |name, options, valid|
    out, err, status = Open3.capture3({'PATH' => work + '/bin:' + ENV.fetch('PATH')}, python, meson, 'setup', work + '/' + name, work, *options)
    abort "FAIL #{name}: #{out}#{err}" unless status.success? == valid
    abort 'Old configuration failed for an unrelated reason' if !valid && !(out + err).include?('CLC requires SPIRV-Tools')
    puts "PASS: actual upstream Meson feature check #{name}"
  end
end
puts 'PASS: real Meson configure boundary; no Mesa compiler build or target execution'
