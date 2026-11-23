/* Locate resources shipped beside the installed Darwin image. */
#ifndef ATSPI_DARWIN_INSTALL_PATH_H
#define ATSPI_DARWIN_INSTALL_PATH_H

#include <dlfcn.h>
#include <glib.h>
#include <stdlib.h>

static gchar *
atspi_install_path (const gchar *path)
{
  static const char image_anchor;
  Dl_info info;

  if (g_path_is_absolute (path))
    return g_strdup (path);
  if (!dladdr (&image_anchor, &info) || info.dli_fname == NULL)
    return NULL;
  g_autofree gchar *image = realpath (info.dli_fname, NULL);
  if (image == NULL)
    return NULL;
  g_autofree gchar *directory = g_path_get_dirname (image);
  g_autofree gchar *prefix = g_path_get_dirname (directory);
  return g_build_filename (prefix, path, NULL);
}

#endif
