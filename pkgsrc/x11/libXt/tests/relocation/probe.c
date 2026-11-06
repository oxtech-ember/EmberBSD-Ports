/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
#include <X11/Xlib.h>
#include <locale.h>
#include <stdio.h>
#include <string.h>
void xlocaledir(char *,int);
int main(void) {
 char b[512],dir[4096];
 XGetErrorDatabaseText(NULL,"RelocProbe","Value","not-found",b,sizeof(b));
 KeySym k=XStringToKeysym("RelocProbeUnique");
 xlocaledir(dir,sizeof(dir));
 setlocale(LC_ALL,"C");
 printf("error=%s keysym=%lx locales=%s supports=%d\n",b,k,dir,XSupportsLocale());
 return 0;
}
