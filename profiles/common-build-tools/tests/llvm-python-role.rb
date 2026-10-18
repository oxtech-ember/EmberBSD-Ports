#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Query actual post-barrier Python build roles.
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: llvm-python-role.rb PKGSRC MAKECONF BMAKE NEW_WORK' unless ARGV.size == 4
pkgsrc, makeconf, bmake = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work + '/pkgsrc/lang')
tree = work + '/pkgsrc'; profile = File.expand_path('..', __dir__)
Dir.children(pkgsrc).reject { |n| n.start_with?('.') || n == 'lang' }.each { |n| File.symlink(pkgsrc + '/' + n, tree + '/' + n) }
Dir.children(pkgsrc + '/lang').reject { |n| %w[llvm llvm-devel].include?(n) }.each { |n| File.symlink(pkgsrc + '/lang/' + n, tree + '/lang/' + n) }
%w[llvm llvm-devel].each { |n| FileUtils.cp_r(profile + '/recipes/lang/' + n, tree + '/lang/' + n) }
vars = %w[PKGNAME WRKDIR CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CMAKE_CONFIGURE_ARGS CONFIGURE_ENV PYTHON_FOR_BUILD_ONLY PYTHONBIN REPLACE_PYTHON DEPENDS BUILD_DEPENDS TOOL_DEPENDS BUILDLINK_DEPMETHOD.py-llvm-lit]
rows = [%w[llvm yes], %w[llvm-devel yes], %w[llvm no]].map do |package, cross|
  output, error, status = Open3.capture3({'MAKECONF' => makeconf}, bmake, '-C', tree + '/lang/' + package,
    '_PKGSRC_BARRIER=yes', 'USE_CROSS_COMPILE=' + cross, 'WRKOBJDIR=' + work + '/objects', *vars.flat_map { |k| ['-V', '${' + k + '}'] })
  abort error unless status.success?
  vars.zip(output.lines.map(&:chomp)).to_h
end
File.write(work + '/query.json', JSON.pretty_generate(rows) + "\n")
runtime, sdk, native = rows
%w[CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CMAKE_CONFIGURE_ARGS CONFIGURE_ENV].each do |field|
  a = runtime.fetch(field).gsub(runtime.fetch('WRKDIR'), '<WORK>')
  b = sdk.fetch(field).gsub(sdk.fetch('WRKDIR'), '<WORK>')
  abort "Cross LLVM compiler inputs differ: #{field}" unless a == b
end
abort 'LLVM role identities differ' unless runtime.fetch('PKGNAME') == 'llvm-23.1.3nb1' && sdk.fetch('PKGNAME') == 'llvm-devel-23.1.3nb2' && native.fetch('PKGNAME') == 'llvm-23.1.3'
abort 'Cross Python is not a native tool' unless [runtime, sdk].all? { |r| r.fetch('PYTHON_FOR_BUILD_ONLY') == 'tool' && r.fetch('TOOL_DEPENDS').match?(/python[0-9]+>=/) }
abort 'Cross lit buildlink role changed' unless [runtime, sdk].all? { |r| r.fetch('BUILDLINK_DEPMETHOD.py-llvm-lit') == 'build' }
abort 'Runtime gained target Python/lit' if runtime.fetch('DEPENDS').match?(/python[0-9]+|llvm-lit/)
abort 'SDK lost target Python/lit' unless sdk.fetch('DEPENDS').match?(/python[0-9]+>=/) && sdk.fetch('DEPENDS').include?('llvm-lit-23.1.3')
abort 'Target shebang changed' unless runtime.fetch('PYTHONBIN') == sdk.fetch('PYTHONBIN') && sdk.fetch('PYTHONBIN').start_with?('/usr/pkg/bin/python') && runtime.fetch('REPLACE_PYTHON') == sdk.fetch('REPLACE_PYTHON')
abort 'Native full Python dependency changed' unless native.fetch('PYTHON_FOR_BUILD_ONLY') == 'no' && native.fetch('CFLAGS').match?(%r{/include/python[0-9.]+}) && native.fetch('DEPENDS').include?('llvm-lit-23.1.3')
puts 'PASS: post-barrier cross compile inputs match; SDK Python/lit and target shebangs remain; native full Python role remains.'
puts 'SCOPE: actual pkgsrc metadata queries; no compiler execution or LLVM package acceptance.'
