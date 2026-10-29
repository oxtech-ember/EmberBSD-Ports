$NetBSD$

Generate secret_token.rb with safe mode.

--- lib/tasks/initializers.rake.orig
+++ lib/tasks/initializers.rake
@@ -20,7 +20,7 @@
 file 'config/initializers/secret_token.rb' do
   path = File.join(Rails.root, 'config', 'initializers', 'secret_token.rb')
   secret = SecureRandom.hex(40)
-  File.open(path, 'w') do |f|
+  File.open(path, 'w', 0640) do |f|
     f.write <<"EOF"
 # frozen_string_literal: true
 
