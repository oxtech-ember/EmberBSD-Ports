#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual upstream test-entry regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: check-tempdir.rb ORIGINAL_BUILD PATCHED_BUILD NEW_OUTPUT' unless ARGV.size == 3
before, fixed = ARGV.take(2).map { |path| File.realpath(path) }
output = File.expand_path(ARGV[2])
abort 'Output exists.' if File.exist?(output) || File.symlink?(output)
FileUtils.mkdir_p(output)
results = []
{
  'OpenEXRTest' => 'testMagic',
  'OpenEXRCoreTest' => 'testBase',
  'OpenEXRUtilTest' => 'testImageChannel'
}.each do |program, test|
  original = before + '/bin/' + program
  repaired = fixed + '/bin/' + program
  abort 'Missing actual test executable.' unless File.executable?(original) && File.executable?(repaired)
  missing = output + '/absent-' + program
  directory = output + '/' + program
  Dir.mkdir(directory)
  [
    ['original-invalid', original, missing],
    ['patched-invalid', repaired, missing],
    ['patched-valid', repaired, directory],
    ['patched-slash', repaired, directory + '/']
  ].each do |name, executable, temporary|
    out, err, status = Open3.capture3({ 'TMPDIR' => temporary }, executable, test)
    label = program + '-' + name
    File.write(output + '/' + label + '.stdout', out)
    File.write(output + '/' + label + '.stderr', err)
    text = out + err
    case name
    when 'original-invalid'
      # The unchanged test either uses its platform default successfully or
      # reports that default's access failure. It must not honor this TMPDIR.
      abort 'Original executable already uses TMPDIR.' if text.include?(missing)
      abort 'Original executable did not report its default directory.' unless text.include?('/var/tmp/')
    when 'patched-invalid'
      abort 'Invalid TMPDIR must fail explicitly.' unless !status.success? && text.include?(missing)
      abort 'Invalid TMPDIR was silently created.' if File.exist?(missing)
    else
      abort 'Actual upstream check failed in the selected directory.' unless status.success? && text.include?(directory)
      abort 'Upstream test did not clean its temporary data.' unless Dir.empty?(directory)
    end
    results << { name: label, executable_sha256: Digest::SHA256.file(executable).hexdigest,
                 test: test, tmpdir: temporary, status: status.exitstatus, signal: status.termsig }
    File.write(output + '/result.json', JSON.pretty_generate(results) + "\n")
  end
end
puts 'PASS: actual upstream test entries use TMPDIR and reject an invalid directory.'
