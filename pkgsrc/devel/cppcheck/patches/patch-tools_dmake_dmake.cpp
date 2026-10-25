$NetBSD$

Keep Cppcheck capabilities with shared current dependencies.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- tools/dmake/dmake.cpp.orig
+++ tools/dmake/dmake.cpp
@@ -759,16 +759,16 @@
          << "\n";
 
     fout << "ifeq ($(HAVE_RULES),yes)\n"
-         << "    PCRE_CONFIG = $(shell which pcre-config)\n"
-         << "    ifeq ($(PCRE_CONFIG),)\n"
-         << "        $(error Did not find pcre-config)\n"
-         << "    endif\n"
-         << "    override CXXFLAGS += $(shell $(PCRE_CONFIG) --cflags)\n"
+         << "    PCRE2_CONFIG ?= pcre2-config\n"
+         << "    ifeq ($(PCRE2_CONFIG),)\n"
+         << "        $(error Set PCRE2_CONFIG to the selected pcre2-config)\n"
+         << "    endif\n"
+         << "    override CXXFLAGS += $(shell $(PCRE2_CONFIG) --cflags)\n"
          << "    override CPPFLAGS += -DHAVE_RULES\n"
          << "    ifdef LIBS\n"
-         << "        LIBS += $(shell $(PCRE_CONFIG) --libs)\n"
+         << "        LIBS += $(shell $(PCRE2_CONFIG) --libs8)\n"
          << "    else\n"
-         << "        LIBS=$(shell $(PCRE_CONFIG) --libs)\n"
+         << "        LIBS=$(shell $(PCRE2_CONFIG) --libs8)\n"
          << "    endif\n"
          << "else ifneq ($(HAVE_RULES),)\n"
          << "    $(error invalid HAVE_RULES value '$(HAVE_RULES)')\n"
