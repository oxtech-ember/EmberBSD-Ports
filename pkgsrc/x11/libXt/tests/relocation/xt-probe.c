/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
#include <X11/Intrinsic.h>
#include <stdio.h>
#include <string.h>
int main(void) {
 char b[256]; XtToolkitInitialize(); XtAppContext app=XtCreateApplicationContext();
 XtAppGetErrorDatabaseText(app,"RelocProbe","Value","Probe","not-found",b,sizeof b,NULL);
 printf("xt-error=%s\n",b); XtDestroyApplicationContext(app); return strcmp(b,"moved-xt-message")!=0;
}
