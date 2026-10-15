#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; query the complete exported recipe with real BSD make.
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: llvm-lit-selection.rb EXPORTED_PKGSRC RECIPE_MAKEFILE BMAKE HOST_MAKECONF CROSS_MAKECONF NEW_OUTPUT' unless ARGV.size == 6
tree, recipe, make, host, cross = ARGV.first(5).map { |p| File.realpath(p) }
out = File.expand_path(ARGV[5])
abort 'Output must not exist' if File.exist?(out)
FileUtils.mkdir_p(out)
queries = %w[PKGNAME _PYTHON_VERSION PYTHONBIN PKG_FAIL_REASON OPSYS MACHINE_ARCH USE_CROSS_COMPILE]
results = []
run = lambda do |name, config, extra, reject|
  argv = [make, '-C', tree + '/devel/py-llvm-lit', '-f', recipe,
    'MAKECONF=' + config, 'WRKOBJDIR=' + out + '/objects', *extra,
    *queries.flat_map { |v| ['-V', '${' + v + '}'] }]
  stdout, stderr, status = Open3.capture3(*argv)
  File.write(out + '/' + name + '.log', stdout + stderr)
  values = stdout.lines.map(&:strip)
  abort "bmake query failed: #{name}: #{stderr}" unless status.success? && values.size == queries.size
  data = queries.zip(values).to_h
  results << {case: name, argv: argv, values: data, exit: status.exitstatus}
  File.write(out + '/receipt.json', JSON.pretty_generate(results) + "\n")
  if reject
    abort "Old/unsupported Python accepted: #{name}" if data['PKG_FAIL_REASON'].empty?
  else
    abort "Wrong Python/provider: #{name}: #{stdout}" unless data['PKGNAME'] == 'py315-llvm-lit-23.1.3' &&
      data['_PYTHON_VERSION'] == '315' && data['PYTHONBIN'].end_with?('/bin/python3.15') && data['PKG_FAIL_REASON'].empty?
  end
  data
end
native = run.call('native', host, [], false)
target = run.call('cross', cross, [], false)
recursive = run.call('native-recursive', cross, ['USE_CROSS_COMPILE=no'], false)
abort 'Cross target changed' unless target['OPSYS'] == 'NetBSD' && target['MACHINE_ARCH'] == 'x86_64'
abort 'Recursive host query inherited target platform' unless recursive['OPSYS'] == native['OPSYS'] &&
  recursive['MACHINE_ARCH'] == native['MACHINE_ARCH'] && recursive['USE_CROSS_COMPILE'] == 'no'
[['native', host], ['cross', cross]].each do |name, config|
  %w[314 316].each { |version| run.call(name + '-reject-' + version, config, ['PYTHON_VERSION_REQD=' + version], true) }
end
puts 'PASS: full native, cross and recursive-host lit recipes select Python315; old/unsupported requests fail'
