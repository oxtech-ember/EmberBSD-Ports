#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Test the real helper main and Waiter with real Qt and a private D-Bus session.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
abort "Usage: #{$PROGRAM_NAME} DISTFILES NEW_OUTPUT QT_PREFIX" unless ARGV.size == 3
archives, work, qt = ARGV.map { |path| File.expand_path(path) }
abort 'Output exists' if File.exist?(work)
FileUtils.mkdir_p(work)
recipe = File.expand_path('../../../../../pkgsrc/x11/plasma6-plasma-workspace', __dir__)
archive = File.join(archives, 'plasma-workspace-6.8.0.tar.xz')
expected = File.read(recipe+'/distinfo')[/^SHA512 \(plasma-workspace-6\.8\.0\.tar\.xz\) = (\h+)$/, 1]
abort 'Archive hash mismatch' unless expected && Digest::SHA512.file(archive).hexdigest == expected
%w[patch-startkde_waitforname_argc patch-startkde_waitforname_bus].each do |name|
  expected = File.read(recipe+'/distinfo')[/^SHA1 \(#{Regexp.escape(name)}\) = (\h+)$/, 1]
  canonical = File.readlines(recipe+'/patches/'+name).reject { |line| line.match?(/\$NetBSD.*/) }.join
  abort "Patch hash mismatch: #{name}" unless expected && Digest::SHA1.hexdigest(canonical) == expected
end
def run(command, log, expected = 0, env = {}, **options)
  env = {'ASAN_OPTIONS'=>'halt_on_error=1', 'UBSAN_OPTIONS'=>'halt_on_error=1'}.merge(env)
  stdout, stderr, status = Open3.capture3(env, *command, rlimit_core: 0, **options)
  File.write(log, command.shelljoin+"\n"+stdout+stderr+"\nexit=#{status.exitstatus} signal=#{status.termsig}\n")
  abort "Unexpected status in #{log}" unless status.exitstatus == expected
  stdout+stderr
end
FileUtils.mkdir_p(work+'/baseline/startkde/waitforname')
%w[waiter.h waiter.cpp main.cpp].each do |name|
  text, status = Open3.capture2('tar','-xOf',archive,'plasma-workspace-6.8.0/startkde/waitforname/'+name)
  abort 'Archive extraction failed' unless status.success?
  File.write(work+'/baseline/startkde/waitforname/'+name,text)
end
# Isolate this failure from the separately proven argc lifetime defect.
run(['patch','-p0','-i',recipe+'/patches/patch-startkde_waitforname_argc'],work+'/patch-argc.log',chdir:work+'/baseline')
FileUtils.cp_r(work+'/baseline',work+'/patched')
run(['patch','-p0','-i',recipe+'/patches/patch-startkde_waitforname_bus'],work+'/patch-bus.log',chdir:work+'/patched')
%w[baseline patched].each do |variant|
  File.write(work+'/'+variant+'/startkde/waitforname/debug_p.h',"#include <QLoggingCategory>\nQ_DECLARE_LOGGING_CATEGORY(LOG_PLASMA)\n")
end
File.write(work+'/debug.cpp',"#include <QLoggingCategory>\nQ_LOGGING_CATEGORY(LOG_PLASMA, \"ember.test.waiter\")\n")
File.write(work+'/CMakeLists.txt',<<~CMAKE)
  cmake_minimum_required(VERSION 3.21)
  project(WaiterBusContract LANGUAGES CXX)
  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_AUTOMOC ON)
  set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
  find_package(Qt6 6.12.0 REQUIRED COMPONENTS Core DBus)
  if(SANITIZE)
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined)
  endif()
  foreach(variant baseline patched)
    add_executable(waiter-${variant} ${variant}/startkde/waitforname/waiter.cpp ${variant}/startkde/waitforname/main.cpp debug.cpp)
    target_include_directories(waiter-${variant} PRIVATE ${variant}/startkde/waitforname)
    target_link_libraries(waiter-${variant} PRIVATE Qt6::Core Qt6::DBus)
  endforeach()
CMAKE
File.write(work+'/session.conf', <<~XML)
  <busconfig>
    <type>session</type>
    <listen>unix:tmpdir=/tmp</listen>
    <auth>EXTERNAL</auth>
    <policy context="default">
      <allow user="#{Process.uid}"/>
      <allow own="*"/>
      <allow send_destination="*"/>
      <allow receive_sender="*"/>
    </policy>
  </busconfig>
XML
query_policy = File.read(work+'/session.conf').sub('  </policy>', '    <deny send_destination="org.freedesktop.DBus" send_interface="org.freedesktop.DBus" send_member="NameHasOwner"/>'+"\n  </policy>")
File.write(work+'/query-denied.conf', query_policy)
cmake = ENV.fetch('CMAKE','cmake')
dbus = ENV.fetch('DBUS_RUN_SESSION','dbus-run-session')
%w[normal sanitized].each do |mode|
  build = work+'/'+mode
  run([cmake,'-S',work,'-B',build,'-DCMAKE_PREFIX_PATH='+qt,'-DCMAKE_BUILD_TYPE=Debug','-DSANITIZE='+(mode=='sanitized' ? 'ON' : 'OFF')],work+'/'+mode+'-configure.log')
  run([cmake,'--build',build,'--parallel','2'],work+'/'+mode+'-build.log')
  %w[baseline patched].each do |variant|
    bin = build+'/waiter-'+variant
    env = {'DBUS_SESSION_BUS_ADDRESS'=>'unix:path='+work+'/absent-socket'}
    %w[registered unregistered].each do |condition|
      args = condition=='unregistered' ? ['--unregistered'] : []
      expected = variant=='baseline' && condition=='unregistered' ? 0 : 1
      log = run([bin,*args,'--timeout','1','org.example.Absent'],work+"/#{mode}-#{variant}-absent-#{condition}.log",expected,env)
      if variant=='patched'
        abort 'Missing bus error diagnostic' unless log.include?('Cannot connect to the session bus:')
      elsif condition=='unregistered'
        abort 'Missing false-success baseline' unless log.include?('is not yet registered')
      end
    end
    # A connected bus can reject the query. Invalid replies must not mean absence.
    %w[registered unregistered].each do |condition|
      args = condition=='unregistered' ? ['--unregistered'] : []
      expected = variant=='baseline' && condition=='unregistered' ? 0 : 1
      log = run([dbus,'--config-file='+work+'/query-denied.conf','--',bin,*args,'--timeout','1','org.example.Absent'],work+"/#{mode}-#{variant}-query-denied-#{condition}.log",expected)
      abort 'Missing query error diagnostic' if variant=='patched' && !log.include?('Cannot query service registration:')
    end
    # Private live bus: already true conditions complete; pending conditions time out.
    [[[], 'org.freedesktop.DBus', 0], [['--unregistered'], 'org.example.Absent', 0],
     [[], 'org.example.Absent', 1], [['--unregistered'], 'org.freedesktop.DBus', 1]].each_with_index do |(args,service,expected),index|
      run([dbus,'--config-file='+work+'/session.conf','--',bin,*args,'--timeout','1',service],work+"/#{mode}-#{variant}-live-#{index}.log",expected)
    end
  end
end
puts 'PASS: baseline false success reproduced; patched D-Bus failures return 1; live registration/unregistration semantics preserved; normal and ASan/UBSan pass'
