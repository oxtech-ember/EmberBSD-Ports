#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual installed host-search regression.
require 'digest'
require 'fileutils'
require 'open3'
abort 'Usage: doctools-host-import.rb INSTALLED_CONFIG NEW_WORK' unless ARGV.length == 2
config=File.realpath(ARGV[0]); work=File.expand_path(ARGV[1]); Dir.mkdir(work)
line=File.readlines(config).find { |l| l.include?('find_file(KDOCTOOLS_TARGETSFILE ') }
abort 'Expected installed host-search statement missing' unless line&.include?('NO_CMAKE_FIND_ROOT_PATH')
FileUtils.mkdir_p(work+'/host/KF6DocTools')
FileUtils.mkdir_p(work+'/target')
File.write(work+'/host/KF6DocTools/KF6DocToolsToolsTargets.cmake', "# Host import fixture.\n")
cmake=ENV.fetch('CMAKE','cmake')
%w[current original absent].each do |kind|
  body=kind=='original' ? line.sub(' NO_CMAKE_FIND_ROOT_PATH','') : line
  script=<<~CMAKE
    set(CMAKE_FIND_ROOT_PATH "#{work}/target")
    set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
    set(KF6_HOST_TOOLING "#{work}/#{kind=='absent' ? 'missing' : 'host'}")
    #{body}
    if(NOT KDOCTOOLS_TARGETSFILE STREQUAL "#{work}/host/KF6DocTools/KF6DocToolsToolsTargets.cmake")
      message(FATAL_ERROR "Host generator import was not selected: ${KDOCTOOLS_TARGETSFILE}")
    endif()
  CMAKE
  File.write(work+"/#{kind}.cmake",script)
  out,result=Open3.capture2e(cmake,'-P',work+"/#{kind}.cmake")
  File.write(work+"/#{kind}.log",out)
  abort "Unexpected #{kind} result" unless result.success? == (kind=='current')
  abort 'Wrong negative failure' if kind!='current' && !out.include?('Host generator import was not selected')
end
File.write(work+'/inputs.sha256',[__FILE__,config].map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: actual installed host import escapes target-only root; original search and missing tools fail'
