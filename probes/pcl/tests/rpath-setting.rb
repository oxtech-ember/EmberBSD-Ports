#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Test the real PCL CMake RPATH block.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

def fail_input(message)
  warn message
  exit 2
end

def run(arguments, log)
  stdout, stderr, status = Open3.capture3(*arguments)
  File.write(log, stdout + stderr)
  raise "Failed (#{status.exitstatus}): #{arguments.inspect}" unless status.success?

  stdout + stderr
end

fail_input('Usage: rpath-setting.rb PCL_ARCHIVE NEW_OUTPUT') unless ARGV.length == 2
archive, work = ARGV
[archive, work].each do |path|
  unless path.match?(%r{\A/[A-Za-z0-9_./-]+\z}) && File.expand_path(path) == path
    fail_input('Use simple absolute paths without dot components or trailing slashes.')
  end
end
fail_input('Output path already exists.') if File.exist?(work) || File.symlink?(work)
fail_input('A regular PCL archive is required.') unless File.file?(archive) && !File.symlink?(archive)

begin
  manifest = File.expand_path('../sources.tsv', __dir__)
  entry = File.readlines(manifest).find { |line| line.start_with?('pcl-') }
  raise 'Missing PCL source manifest entry' unless entry

  _name, expected_archive, url = entry.split
  commit = url&.match(%r{\Ahttps://codeload\.github\.com/PointCloudLibrary/pcl/tar\.gz/([0-9a-f]{40})\z})&.captures&.first
  raise 'Invalid PCL source manifest entry' unless commit && expected_archive&.match?(/\A[0-9a-f]{64}\z/)
  raise 'Wrong PCL source archive SHA256' unless Digest::SHA256.file(archive).hexdigest == expected_archive

  patch = File.expand_path('../../../pkgsrc/graphics/pcl/patches/patch-cmake-rpath', __dir__)
  raise 'Missing canonical PCL RPATH patch' unless File.file?(patch)

  FileUtils.mkdir_p("#{work}/pristine")
  run(['tar', '-xzf', archive, '-C', "#{work}/pristine", '--strip-components=1',
       "pcl-#{commit}/CMakeLists.txt"], "#{work}/extract.log")
  baseline = File.read("#{work}/pristine/CMakeLists.txt")
  dry = run(['patch', '--dry-run', '--fuzz=0', '-p1', '-d', "#{work}/pristine", '-i', patch],
            "#{work}/pristine-dryrun.log")
  raise 'Patch applied with an offset or fuzz' if dry.match?(/offset|fuzz/i)

  applied = run(['patch', '--fuzz=0', '-p1', '-d', "#{work}/pristine", '-i', patch], "#{work}/apply.log")
  raise 'Patch applied with an offset or fuzz' if applied.match?(/offset|fuzz/i)

  final = File.read("#{work}/pristine/CMakeLists.txt")
  {'baseline' => baseline, 'final' => final}.each do |name, source|
    block = source.match(/^set\(CMAKE_SKIP_BUILD_RPATH  FALSE\).*?(?=^### ---\[ Find universal dependencies)/m)
    raise 'Missing actual PCL RPATH block' unless block

    File.write("#{work}/#{name}.cmake", block[0])
  end
  fixture = <<~'CMAKE'
    cmake_minimum_required(VERSION 3.22)
    set(CMAKE_INSTALL_PREFIX /usr/pkg)
    set(LIB_INSTALL_DIR lib)
    set(CMAKE_PLATFORM_IMPLICIT_LINK_DIRECTORIES /lib /usr/lib)
    include("${BLOCK}")
    if(NOT "${CMAKE_BUILD_WITH_INSTALL_RPATH}" STREQUAL "${EXPECTED}")
      message(FATAL_ERROR "Expected ${EXPECTED}; got ${CMAKE_BUILD_WITH_INSTALL_RPATH}")
    endif()
    if(NOT CMAKE_INSTALL_RPATH STREQUAL "/usr/pkg/lib")
      message(FATAL_ERROR "Unexpected install RPATH ${CMAKE_INSTALL_RPATH}")
    endif()
    file(WRITE "${RESULT}" "${CMAKE_BUILD_WITH_INSTALL_RPATH}\n")
  CMAKE
  File.write("#{work}/fixture.cmake", fixture)
  cases = []
  %w[baseline final].each do |name|
    [nil, 'ON', 'OFF'].each do |setting|
      expected = name == 'final' && setting ? setting : 'FALSE'
      label = "#{name}-#{setting || 'undefined'}"
      arguments = ['cmake', "-DBLOCK=#{work}/#{name}.cmake", "-DEXPECTED=#{expected}",
                   "-DRESULT=#{work}/#{label}.result"]
      arguments << "-DCMAKE_BUILD_WITH_INSTALL_RPATH=#{setting}" if setting
      arguments += ['-P', "#{work}/fixture.cmake"]
      run(arguments, "#{work}/#{label}.log")
      cases << {source: name, caller: setting, expected: expected,
                actual: File.read("#{work}/#{label}.result").strip, status: 0}
    end
  end
  version = run(['cmake', '--version'], "#{work}/cmake-version.log").lines.first.strip
  receipt = {
    source_archive_sha256: expected_archive,
    baseline_cmake_sha256: Digest::SHA256.hexdigest(baseline),
    final_cmake_sha256: Digest::SHA256.hexdigest(final),
    patch_sha256: Digest::SHA256.file(patch).hexdigest,
    cmake_version: version,
    pristine_patch_fuzz: 0, pristine_patch_offset: 0,
    cases: cases,
    limitation: 'The CMake script fixture uses the real source RPATH block. No PCL build is claimed.'
  }
  File.write("#{work}/summary.json", JSON.pretty_generate(receipt) + "\n")
  puts 'PASS: zero-fuzz pristine patch and six bounded RPATH configuration regression cases'
rescue StandardError => error
  warn "FAIL: #{error.message}"
  exit 1
end
