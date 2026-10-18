#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Query current pkgsrc inputs at the shared root.
require 'json'
require 'open3'
require 'rbconfig'
require 'shellwords'
require_relative 'reuse-package-stage'

module LLVMPkgsrcInputs
  FLAGS = %w[CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CMAKE_CONFIGURE_ARGS CONFIGURE_ENV
             CC CXX CPP AR AS LD RANLIB STRIP CWRAPPERS_APPEND.cc CWRAPPERS_APPEND.cxx
             PKG_OPTIONS _CMAKE_BUILD_SYSTEM INSTALL_TARGET CMAKE_INSTALL_ARGS
             LLVM_TARGETS_TO_BUILD LLVM_EXPERIMENTAL_TARGETS_TO_BUILD
             CROSS_DESTDIR TOOLDIR MACHINE_GNU_PLATFORM TOOL_PYTHONBIN
             EMBERBSD_LLVM_NATIVE_TOOLS].freeze
  FIELDS = (FLAGS + %w[PKGNAME PKGPATH USE_CROSS_COMPILE OPSYS OS_VERSION MACHINE_ARCH
                       LLVM_VERSION WRKDIR WRKSRC CMAKE_BUILD_DIR EMBERBSD_LLVM_PKGDIR
                       CMAKE PERL5 .MAKE.MAKEFILES PKG_FAIL_REASON]).freeze
  module_function

  def prepare(template, output, bmake, package)
    value = JSON.parse(File.binread(template))
    work = value.fetch('runtime_work')
    LLVMStageReuse.check(work.start_with?('/') && File.directory?(work), 'Existing runtime_work required')
    package = File.realpath(package)
    # Keep MAKEFLAGS: command-line overrides must reach the current query.
    # Query at the actual common build root. Never rewrite flag or env strings.
    # Skip phase caches so current headers/providers and recipes are queried.
    command = [bmake, '-C', package, '_PKGSRC_BARRIER=yes', '_MAKEVARS_MK=defined',
               'EMBERBSD_LLVM_REUSE_QUERY=yes', 'WRKDIR=' + work,
               *FIELDS.flat_map { |key| ['-v', key] }]
    out, error, status = Open3.capture3(*command)
    LLVMStageReuse.check(status.success?, "Current pkgsrc query failed: #{error}")
    lines = out.lines.map(&:chomp)
    LLVMStageReuse.check(lines.size == FIELDS.size, 'Invalid current pkgsrc query')
    row = FIELDS.zip(lines).to_h
    LLVMStageReuse.check(row.fetch('PKG_FAIL_REASON').empty?, 'Current pkgsrc inputs failed: ' + row.fetch('PKG_FAIL_REASON'))
    LLVMStageReuse.check(row.fetch('USE_CROSS_COMPILE') == 'yes' &&
                        %w[lang/llvm lang/llvm-devel].include?(row.fetch('PKGPATH')), 'Cross LLVM package required')
    target = value.fetch('target')
    {'OPSYS' => 'opsys', 'OS_VERSION' => 'version', 'MACHINE_ARCH' => 'arch',
     'MACHINE_GNU_PLATFORM' => 'triple'}.each do |field, key|
      LLVMStageReuse.check(row.fetch(field) == target.fetch(key), "Current target differs: #{field}")
    end
    LLVMStageReuse.check(row.fetch('LLVM_VERSION') == value.fetch('version'), 'Current LLVM version differs')
    LLVMStageReuse.check(row.fetch('WRKDIR') == work && row.fetch('WRKSRC') == value.fetch('source') &&
                        row.fetch('WRKSRC') + '/' + row.fetch('CMAKE_BUILD_DIR') == value.fetch('build'), 'Current LLVM source/build root differs')
    LLVMStageReuse.check(%w[install install/strip].include?(row.fetch('INSTALL_TARGET')), 'Unsupported CMake install target')
    recipe = File.realpath(row.fetch('EMBERBSD_LLVM_PKGDIR'))
    sdk = File.realpath(recipe + '/../llvm-devel')
    LLVMStageReuse.check(recipe == File.realpath(value.fetch('recipe')) && sdk == File.realpath(value.fetch('sdk_recipe')),
                        'Current recipe roots differ')
    value['flags'] = row.slice(*FLAGS)
    value['install_strip'] = row.fetch('INSTALL_TARGET') == 'install/strip'
    value['cmake'] = File.realpath(row.fetch('CMAKE'))
    value['perl'] = File.realpath(row.fetch('PERL5'))
    files = value.fetch('files')
    # These lists are an explicit, separately reviewed inventory. Include the
    # selected compiler internals, wrappers, target headers and link inputs.
    %w[compiler native_tools patches target_abi].each do |kind|
      LLVMStageReuse.check(files.fetch(kind).is_a?(Array) && !files.fetch(kind).empty?, "Missing #{kind} inventory")
    end
    compiler_roots = files.fetch('compiler').map { |path| File.realpath(path) }
    %w[gcc g++ strip].each do |name|
      driver = row.fetch('TOOLDIR') + '/bin/' + target.fetch('triple') + '-' + name
      LLVMStageReuse.check(compiler_roots.include?(File.realpath(driver)), "Current compiler tool missing from inventory: #{name}")
    end
    native = [bmake, RbConfig.ruby, value.fetch('cmake'), value.fetch('perl'), row.fetch('TOOL_PYTHONBIN')]
    %w[llvm-tblgen llvm-min-tblgen llvm-config].each { |name| native << row.fetch('EMBERBSD_LLVM_NATIVE_TOOLS') + '/' + name }
    files['native_tools'] = (files.fetch('native_tools') + native.map { |path| File.realpath(path) }).uniq.sort
    makefiles = Shellwords.split(row.fetch('.MAKE.MAKEFILES')).map { |path| File.realpath(File.expand_path(path, package)) }
    files['pkgsrc'] = makefiles.reject { |path| [recipe, sdk].any? { |root| path.start_with?(root + '/') } }.uniq.sort
    LLVMStageReuse.check(output.start_with?('/') && File.directory?(File.dirname(output)) && !File.symlink?(output), 'Regular context output path required')
    canonical = File.realpath(File.dirname(output)) + '/' + File.basename(output)
    LLVMStageReuse.check(!LLVMStageReuse.overlaps(canonical, LLVMStageReuse.input_roots(value)), 'Context output overlaps LLVM inputs')
    protected = files.values.flatten + value.fetch('manifests').values + [template, value.fetch('runtime').fetch('archive')]
    LLVMStageReuse.check(!protected.any? { |path| File.realpath(path) == canonical }, 'Context output replaces an input')
    File.write(output, JSON.pretty_generate(value) + "\n")
    LLVMStageReuse.context(output)
    puts 'PASS: current pkgsrc flags were queried at the common LLVM build root without string normalization.'
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    raise 'Usage: prepare-reuse-inputs.rb TEMPLATE OUTPUT BMAKE PACKAGE_DIRECTORY' unless ARGV.size == 4
    LLVMPkgsrcInputs.prepare(*ARGV)
  rescue StandardError => e
    warn "FAIL: #{e.message}"
    exit 1
  end
end
