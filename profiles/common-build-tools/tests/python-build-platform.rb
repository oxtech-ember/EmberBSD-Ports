#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Use real pkgsrc metadata and host generator.
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: python-build-platform.rb PKGSRC CROSS_MAKECONF PYTHON_SOURCE PYTHON_BUILD HOST_PYTHON NEW_WORK' unless ARGV.length == 6
tree, config, source, build, python = ARGV.first(5).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
# Reuse the actual framework read-only; replace only this recipe in a private tree.
FileUtils.mkdir_p(work + '/pkgsrc/lang')
Dir.children(tree).each { |p| File.symlink(tree + '/' + p, work + '/pkgsrc/' + p) unless p == 'lang' }
Dir.children(tree + '/lang').each { |p| File.symlink(tree + '/lang/' + p, work + '/pkgsrc/lang/' + p) unless p == 'python315' }
recipe = File.expand_path('../../../pkgsrc/lang/python315', __dir__)
FileUtils.cp_r(recipe, work + '/pkgsrc/lang/python315')
vars = %w[MAKE_ENV OPSYS OS_VERSION MACHINE_ARCH CROSS_MACHINE_ARCH PKG_FAIL_REASON]
command = [make, '-C', work + '/pkgsrc/lang/python315', 'MAKECONF=' + config, 'WRKOBJDIR=' + work + '/objects', *vars.flat_map { |v| ['-V', '${' + v + '}'] }]
out, err, status = Open3.capture3(*command)
File.write(work + '/metadata.stdout', out); File.write(work + '/metadata.stderr', err)
abort 'actual pkgsrc metadata query failed: ' + err unless status.success?
values = out.lines.map(&:chomp)
abort 'unexpected metadata query output' unless values.length == vars.length
v = vars.zip(values).to_h
abort 'real amd64 target metadata required' unless v.values_at('OPSYS', 'OS_VERSION', 'MACHINE_ARCH', 'CROSS_MACHINE_ARCH') == %w[NetBSD 11.0 x86_64 x86_64] && v.fetch('PKG_FAIL_REASON').empty?
platforms = Shellwords.split(v.fetch('MAKE_ENV')).grep(/^PYTHON_BUILD_DETAILS_PLATFORM=/)
abort 'duplicate declared runtime platform' if platforms.length > 1
platform = platforms.first&.split('=', 2)&.last
makefile = File.read(build + '/Makefile')
host_platform = makefile[/^_PYTHON_HOST_PLATFORM=\s*(\S+)$/, 1]
abort 'actual build target platform mismatch' unless host_platform == 'netbsd11-x86_64'
relative = File.read(build + '/pybuilddir.txt').strip
configdir = File.realpath(build + '/' + relative)
abort 'target sysconfig path escaped build' unless configdir.start_with?(build + '/')
datafiles = Dir.glob(configdir + '/_sysconfigdata_*.py')
abort 'one actual target sysconfig module required' unless datafiles.length == 1
module_name = File.basename(datafiles.fetch(0), '.py')
env = {'PYTHONDONTWRITEBYTECODE' => '1', 'PYTHONHOME' => nil,
       '_PYTHON_PROJECT_BASE' => build, '_PYTHON_HOST_PLATFORM' => host_platform,
       'PYTHONPATH' => source + '/Lib', '_PYTHON_SYSCONFIGDATA_NAME' => module_name,
       '_PYTHON_SYSCONFIGDATA_PATH' => configdir,
       'PYTHON_BUILD_DETAILS_PLATFORM' => platform}
out, status = Open3.capture2e(env, python, '-B', source + '/Tools/build/generate-build-details.py', work + '/build-details.json')
File.write(work + '/generator.log', out)
abort 'FAIL: actual generator did not receive target platform from MAKE_ENV: ' + out unless status.success?
details = JSON.parse(File.read(work + '/build-details.json'))
abort 'incorrect target runtime platform' unless platform == 'netbsd-11.0-amd64' && details.fetch('platform') == platform
abort 'target version changed' unless details.dig('language', 'version_info').values_at('major', 'minor', 'micro') == [3, 15, 0]
abort 'target loader suffixes changed' unless details.dig('suffixes', 'extensions') == %w[.cpython-315.so .abi3.so .so]
abort 'target static path changed' unless details.dig('libpython', 'static') == '/usr/pkg/lib/python3.15/config-3.15/libpython3.15.a'
puts 'PASS: real pkgsrc MAKE_ENV supplies NetBSD11 amd64 runtime platform to actual generator'
puts 'PASS: target source version, loader suffixes and installed static path retained'
