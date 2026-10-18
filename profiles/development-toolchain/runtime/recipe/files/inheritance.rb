# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted provenance for a fresh libstdc++ rebuild.
module GCC16Runtime
  module Inheritance
    PATCH = 'patch-libstdc++-v3_config_locale_generic_c__locale'
    PATCH_SHA256 = '35a5220459db81dd19376dec091837fca12c24e3e2c1a8518af0536f3ed20fa2'.freeze
    PARENT_FILES = %w[inputs.txt stage.sha256 stage.symlinks build-success].freeze
    CONFIG_FILES = %w[commands.json configuration/config.status configuration/config.h].freeze
    CRT_FILES = %w[crtbegin.o crtbeginS.o crtbeginT.o crtend.o crtendS.o crtfastmath.o libgcc.a libgcc_eh.a libgcov.a].freeze
    module_function

    def hash(path)
      Digest::SHA256.file(path).hexdigest
    end

    def inventory(root)
      result = {}
      Find.find(root) do |path|
        next if File.directory?(path) && !File.symlink?(path)
        name = path.delete_prefix(root + '/')
        raise Invalid, 'Unsafe component path' unless name.match?(%r{\A[A-Za-z0-9_+./-]+\z}) && !name.split('/').include?('..')
        result[name] = if File.symlink?(path)
          {'link' => File.readlink(path)}
        elsif File.file?(path)
          {'sha256' => hash(path), 'mode' => File.stat(path).mode & 07777}
        else
          raise Invalid, 'Special component file'
        end
      end
      result
    end

    def check_delta(old_recipe, new_recipe)
      select = lambda do |path|
        names = %w[distinfo Makefile Makefile.common] + Dir.children(path + '/patches').map { |n| 'patches/' + n }
        names.to_h do |name|
          file = path + '/' + name
          raise Invalid, 'Recipe inputs must be regular files' unless File.file?(file) && !File.symlink?(file)
          [name, hash(file)]
        end
      end
      old = select.call(old_recipe)
      current = select.call(new_recipe)
      # Ignore no recipe files. A newly added or changed compiler/runtime patch
      # requires a different build, not inheritance under this bounded mode.
      raise Invalid, 'Unexpected recipe file selection' unless current.keys.sort == (old.keys + ['patches/' + PATCH]).sort
      old.each do |name, entry|
        next if %w[Makefile distinfo].include?(name)
        raise Invalid, "Changed inherited recipe input: #{name}" unless current[name] == entry
      end
      patch = new_recipe + '/patches/' + PATCH
      raise Invalid, 'Unsupported locale source patch' unless hash(patch) == PATCH_SHA256
      make = File.read(old_recipe + '/Makefile')
      raise Invalid, 'Unexpected old compiler revision' unless make.scan(/^PKGREVISION=\s*1$/).size == 1
      expected_make = make.sub(/^(PKGREVISION=\s*)1$/) { "#{$1}2" }
      raise Invalid, 'Unexpected compiler recipe change' unless File.read(new_recipe + '/Makefile') == expected_make
      patch_sha1 = Digest::SHA1.hexdigest(File.readlines(patch).reject { |l| l.match?(/[$]NetBSD.*/) }.join)
      line = "SHA1 (#{PATCH}) = #{patch_sha1}\n"
      info = File.read(new_recipe + '/distinfo')
      raise Invalid, 'Unexpected patch manifest change' unless info.lines.count(line) == 1 && info.sub(line, '') == File.read(old_recipe + '/distinfo')
    end

    def inherited_paths(parent)
      paths = parent.fetch(:files).reject { |p| File.basename(p).start_with?('libstdc++') }.map { |p| 'usr/pkg/' + p }
      triplet = parent.fetch(:metadata).fetch('GCC_RUNTIME_TRIPLET')
      paths + CRT_FILES.map { |f| "usr/pkg/gcc16/lib/gcc/#{triplet}/#{VERSION}/#{f}" }
    end

    def verify(work, pkgsrc, archive, current, expected_source: SOURCE_SHA256)
      file = work + '/inheritance.json'
      receipt = JSON.parse(File.read(file))
      raise Invalid, 'Unknown inheritance format' unless receipt.fetch('format') == 1
      raise Invalid, 'Inheritance receipt is not pinned by inputs' unless File.readlines(work + '/inputs.txt').count("#{hash(file)}  #{file}\n") == 1
      PARENT_FILES.each do |name|
        raise Invalid, 'Changed parent receipt' unless hash(work + '/parent/' + name) == receipt.fetch('parent_receipts').fetch(name)
      end
      parent = Stage.new(work + '/parent', work + '/parent-recipe', archive,
        expected_source: expected_source, receipt_paths: receipt.fetch('parent_paths'), allow_rebuild: false).verify
      %w[GCC_RUNTIME_TARGET GCC_RUNTIME_TRIPLET GCC_RUNTIME_LIBRARIES EMBERBSD_SEED_SOURCE].each do |key|
        raise Invalid, 'Parent runtime identity changed' unless parent[:metadata][key] == current[:metadata][key]
      end
      check_delta(work + '/parent-recipe/lang/gcc16', pkgsrc + '/lang/gcc16')
      old = inventory(work + '/parent/stage')
      inherited = inherited_paths(parent).to_h { |p| [p, old.fetch(p)] }
      raise Invalid, 'Incorrect inherited component selection' unless receipt.fetch('inherited') == inherited
      fresh = receipt.fetch('rebuilt')
      raise Invalid, 'Missing fresh libstdc++ headers' unless fresh.key?('usr/pkg/gcc16/include/c++/vector') && fresh.key?("usr/pkg/gcc16/include/c++/#{current[:metadata]['GCC_RUNTIME_TRIPLET']}/bits/c++locale.h")
      raise Invalid, 'Overlapping component ownership' unless (fresh.keys & inherited.keys).empty?
      raise Invalid, 'Foreign rebuilt component' unless fresh.keys.all? { |p| p.start_with?('usr/pkg/gcc16/') && !p.match?(%r{/lib/(?:gcc/|libgcc|libgomp|libatomic)}) }
      runtime = fresh.select { |p, x| p.match?(%r{/lib/libstdc\+\+\.so\.7(?:\.[0-9]+)*\z}) && x.key?('sha256') }
      raise Invalid, 'Missing or unchanged rebuilt libstdc++ DSO' unless runtime.size == 1 && runtime.all? { |p, x| old[p] && old[p]['sha256'] != x['sha256'] }
      raise Invalid, 'Incorrect assembled component bytes' unless inventory(work + '/stage') == fresh.merge(inherited)
      %w[configure.log runtime-build.log runtime-install.log].each do |name|
        raise Invalid, 'Missing or changed genuine build log' unless hash(work + '/' + name) == receipt.fetch('build_logs').fetch(name)
      end
      CONFIG_FILES.each do |name|
        path = work + '/' + name
        raise Invalid, 'Changed build configuration' unless hash(path) == receipt.fetch('configuration').fetch(name) && File.readlines(work + '/inputs.txt').count("#{hash(path)}  #{path}\n") == 1
      end
      {'GCC_RUNTIME_BUILD_MODE' => 'standalone-libstdcxx', 'GCC_RUNTIME_INHERITANCE_SHA256' => hash(file),
       'GCC_RUNTIME_PARENT_INPUTS_SHA256' => receipt['parent_receipts']['inputs.txt'],
       'GCC_RUNTIME_PARENT_STAGE_SHA256' => receipt['parent_receipts']['stage.sha256']}
    rescue KeyError, JSON::ParserError => e
      raise Invalid, "Invalid inheritance receipt: #{e.message}"
    end
  end
end
