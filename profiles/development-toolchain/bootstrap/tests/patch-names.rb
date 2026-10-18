#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); execute actual source audits without extraction.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: patch-names.rb EXPORTED_PKGSRC GCC_ARCHIVE NEW_WORK' unless ARGV.size == 3
tree, archive = ARGV.take(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[2])
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
profile = File.expand_path('../..', __dir__)
recipe = tree + '/lang/gcc16'
name = 'patch-libstdc++-v3_config_locale_generic_c__locale'
abort 'Use the current locale recipe.' unless File.file?(recipe + '/patches/' + name)
FileUtils.mkdir_p(work)
FileUtils.cp_r(recipe, work + '/recipe')
recipe = work + '/recipe'
manifest = File.binread(recipe + '/distinfo')
audits = { 'bootstrap' => File.read(profile + '/bootstrap/audit-source.sh') }
cross = File.read(profile + '/cross/build.sh')
start = cross.index("expected=$(awk -F")
stop = cross.index('mkdir -p "$work"', start || 0)
abort 'Cross audit boundaries changed.' unless start && stop
audits['cross'] = cross[start...stop]
before_guard = '[!A-Za-z0-9_.-]'
after_guard = '[!A-Za-z0-9_.+-]'
results = []
run = lambda do |label, script, expected_status, diagnostic|
  out, err, status = Open3.capture3('sh', '-eu', '-c',
    'profile=$1 recipe=$2 archive=$3; . "$4"', 'audit', profile, recipe, archive, script,
    chdir: work)
  File.write(work + '/' + label + '.stdout', out)
  File.write(work + '/' + label + '.stderr', err)
  results << { name: label, status: status.exitstatus, expected_status: expected_status,
               script_sha256: Digest::SHA256.file(script).hexdigest }
  File.write(work + '/result.json', JSON.pretty_generate(results) + "\n")
  abort "Unexpected result: #{label}" unless status.exitstatus == expected_status &&
    (diagnostic.nil? || err.include?(diagnostic))
end
audits.each do |kind, source|
  abort 'Expected one patch-name guard.' unless source.scan(after_guard).size == 1
  fixed = work + '/' + kind + '.sh'
  baseline = work + '/' + kind + '-before.sh'
  File.write(fixed, source)
  File.write(baseline, source.sub(after_guard, before_guard))
  run.call(kind + '-before', baseline, 1, 'Invalid patch name.')
  run.call(kind + '-current', fixed, 0, nil)
  %w[patch-../escape patch-/absolute patch-$HOME patch-;command patch-`command`
     patch-"quote patch-'quote patch-*.c patch-?.c patch-[abc]].each_with_index do |bad, i|
    File.binwrite(recipe + '/distinfo', "SHA1 (#{bad}) = #{'0' * 40}\n" + manifest)
    run.call(kind + "-unsafe-#{i}", fixed, 1, 'Invalid patch name.')
  end
  File.binwrite(recipe + '/distinfo', manifest)
  original = File.binread(recipe + '/patches/' + name)
  begin
    File.binwrite(recipe + '/patches/' + name, original + "\ncorrupted patch\n")
    run.call(kind + '-corrupt-hash', fixed, 1, 'Patch SHA1 mismatch:')
  ensure
    File.binwrite(recipe + '/patches/' + name, original)
  end
end
puts "PASS: #{results.size} real source-audit results; no extraction or compilation."
