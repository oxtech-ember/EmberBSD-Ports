/* SPDX-License-Identifier: MIT */
/* Execute the native libinput event bridge extracted from the recipe patch. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t usec_t;
struct normalized_coords { double x, y; };
struct wscons_event { int type, value; };
enum { WSCONS_EVENT_GESTURE_PINCH_BEGIN=23, WSCONS_EVENT_GESTURE_PINCH_SCALE,
 WSCONS_EVENT_GESTURE_PINCH_END, WSCONS_EVENT_GESTURE_PINCH_CANCEL };
enum { LIBINPUT_EVENT_GESTURE_PINCH_BEGIN, LIBINPUT_EVENT_GESTURE_PINCH_UPDATE };
struct wscons_pinch { bool active; double scale; };
struct libinput_device { bool pinches; struct wscons_pinch pinch; };
#define wscons_device(d) (d)
static char events[64];
static double scales[64];
static unsigned nevents;
static void gesture_notify_pinch(struct libinput_device *d, usec_t t, int type,
 int fingers, const struct normalized_coords *a,const struct normalized_coords *b,double scale,double angle)
{
 (void)d;(void)t;
 if(fingers!=2 || a->x || a->y || b->x || b->y || angle) abort();
 events[nevents]=type==LIBINPUT_EVENT_GESTURE_PINCH_BEGIN?'B':'U';scales[nevents++]=scale;
}
static void gesture_notify_pinch_end(struct libinput_device *d,usec_t t,int fingers,double scale,bool cancel)
{
 (void)d;(void)t;if(fingers!=2)abort();events[nevents]=cancel?'X':'E';scales[nevents++]=scale;
}
#include "pinch-extract.h"
#ifndef HAVE_PINCH_BRIDGE
/* Old production patch has no pinch event cases: wscons ignores the event. */
static bool wscons_pinch_process(struct libinput_device *d,struct wscons_event *e,usec_t t)
{ (void)d;(void)e;(void)t;return false; }
static void wscons_pinch_cancel(struct libinput_device *d,usec_t t){(void)d;(void)t;}
#endif
#define CHECK(c) do { if(!(c)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);return 1;} }while(0)
static void send(struct libinput_device *d,int type,int value)
{struct wscons_event e={type,value};wscons_pinch_process(d,&e,1000);}
int main(void)
{
 struct libinput_device d={.pinches=true};
 send(&d,23,2);send(&d,24,98304);send(&d,25,0);
 CHECK(nevents==3 && memcmp(events,"BUE",3)==0);
 CHECK(scales[0]==1 && scales[1]==1.5 && scales[2]==1.5 && !d.pinch.active);
 nevents=0;send(&d,24,65536);send(&d,25,0);CHECK(nevents==0);
 send(&d,23,2);send(&d,24,32768);send(&d,26,0);
 CHECK(nevents==3 && memcmp(events,"BUX",3)==0 && scales[2]==.5);
 nevents=0;send(&d,23,2);send(&d,23,2);CHECK(nevents==3 && memcmp(events,"BXB",3)==0);
 wscons_pinch_cancel(&d,2000);CHECK(nevents==4 && events[3]=='X' && !d.pinch.active);
 wscons_pinch_cancel(&d,2000);CHECK(nevents==4);
 nevents=0;d.pinches=false;send(&d,23,2);send(&d,24,90000);CHECK(nevents==0);
 d.pinches=true;send(&d,23,3);CHECK(nevents==0);
 send(&d,23,2);send(&d,24,0);CHECK(nevents==2 && events[1]=='X' && !d.pinch.active);
 puts("native pinch bridge: PASS (scale, cancellation, malformed events, capability)");
 return 0;
}
