$NetBSD$

Build with SDL3 and SDL3_mixer when CCLESTE_SDL3 is defined (sdl30compat.inc.c).
Origin: EmberBSD (AI-assisted); upstream status: not submitted.

--- sdl12main.c.orig
+++ sdl12main.c
@@ -1,8 +1,22 @@
+#ifdef CCLESTE_SDL3
+#define SDL_ENABLE_OLD_NAMES
+#include <SDL3/SDL.h>
+#include <SDL3_mixer/SDL_mixer.h>
+#include "sdl30compat.inc.c"
+#else
 #include <SDL.h>
 #include <SDL_mixer.h>
 #if SDL_MAJOR_VERSION >= 2
 #include "sdl20compat.inc.c"
 #endif
+#define SDL_INIT_OK(r) ((r) == 0)
+#define SURFACE_BITSPP(s) ((s)->format->BitsPerPixel)
+#define SURFACE_BYTESPP(s) ((s)->format->BytesPerPixel)
+#define SURFACE_MAPRGB(s, r, g, b) SDL_MapRGB((s)->format, (r), (g), (b))
+#define SURFACE_LOCKED(s) ((s)->locked)
+#define SURFACE_CLIP(s, rc) (*(rc) = (s)->clip_rect)
+#define EV_KEY(ev) ((ev).key.keysym.sym)
+#endif
 #include <math.h>
 #include <stdarg.h>
 #include <stdio.h>
@@ -71,7 +85,7 @@
 
 static inline Uint32 getcolor(char idx) {
 	SDL_Color c = palette[idx%16];
-	return SDL_MapRGB(screen->format, c.r,c.g,c.b);
+	return SURFACE_MAPRGB(screen, c.r,c.g,c.b);
 }
 
 static void ResetPalette(void) {
@@ -96,7 +110,7 @@
 }
 
 static Uint32 getpixel(SDL_Surface *surface, int x, int y) {
-	int bpp = surface->format->BytesPerPixel;
+	int bpp = SURFACE_BYTESPP(surface);
 	/* Here p is the address to the pixel we want to retrieve */
 	Uint8 *p = (Uint8 *)surface->pixels + y * surface->pitch + x * bpp;
 
@@ -262,7 +276,7 @@
 		if (down & (1u << i)) {
 			SDL_Event ev;
 			ev.type = SDL_KEYDOWN;
-			ev.key.keysym.sym = n3ds_key_map[i];
+			EV_KEY(ev) = n3ds_key_map[i];
 			SDL_PushEvent(&ev);
 		}
 	}
@@ -272,7 +286,7 @@
 #endif
 
 int main(int argc, char** argv) {
-	SDL_CHECK(SDL_Init(SDL_INIT_AUDIO | SDL_INIT_VIDEO) == 0);
+	SDL_CHECK(SDL_INIT_OK(SDL_Init(SDL_INIT_AUDIO | SDL_INIT_VIDEO)));
 #if SDL_MAJOR_VERSION >= 2
 	SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER);
 	SDL_GameControllerAddMappingsFromRW(SDL_RWFromFile("gamecontrollerdb.txt", "rb"), 1);
@@ -479,25 +493,25 @@
 #if SDL_MAJOR_VERSION >= 2
 			if (ev.key.repeat) break; //no key repeat
 #endif
-			if (ev.key.keysym.sym == SDLK_ESCAPE) { //do pause
+			if (EV_KEY(ev) == SDLK_ESCAPE) { //do pause
 				toggle_pause:
 				if (paused) Mix_Resume(-1), Mix_ResumeMusic(); else Mix_Pause(-1), Mix_PauseMusic();
 				paused = !paused;
 				break;
-			} else if (ev.key.keysym.sym == SDLK_DELETE) { //exit
+			} else if (EV_KEY(ev) == SDLK_DELETE) { //exit
 				press_exit:
 				running = 0;
 				break;
-			} else if (ev.key.keysym.sym == SDLK_F11 && !(kbstate[SDLK_LSHIFT] || kbstate[SDLK_ESCAPE])) {
+			} else if (EV_KEY(ev) == SDLK_F11 && !(kbstate[SDLK_LSHIFT] || kbstate[SDLK_ESCAPE])) {
 				if (SDL_WM_ToggleFullScreen(screen)) { //this doesn't work on windows..
 					OSDset("toggle fullscreen");
 				}
 				screen = SDL_GetVideoSurface();
 				break;
-			} else if (0 && ev.key.keysym.sym == SDLK_5) {
+			} else if (0 && EV_KEY(ev) == SDLK_5) {
 				Celeste_P8__DEBUG();
 				break;
-			} else if (ev.key.keysym.sym == SDLK_s && kbstate[SDLK_LSHIFT]) { //save state
+			} else if (EV_KEY(ev) == SDLK_s && kbstate[SDLK_LSHIFT]) { //save state
 				save_state:
 				game_state = game_state ? game_state : SDL_malloc(Celeste_P8_get_state_size());
 				if (game_state) {
@@ -506,7 +520,7 @@
 					game_state_music = current_music;
 				}
 				break;
-			} else if (ev.key.keysym.sym == SDLK_d && kbstate[SDLK_LSHIFT]) { //load state
+			} else if (EV_KEY(ev) == SDLK_d && kbstate[SDLK_LSHIFT]) { //load state
 				load_state:
 				if (game_state) {
 					OSDset("load state");
@@ -521,9 +535,9 @@
 				break;
 			} else if ( //toggle screenshake (e / L+R)
 #ifdef _3DS
-					(ev.key.keysym.sym == SDLK_d && kbstate[SDLK_s]) || (ev.key.keysym.sym == SDLK_s && kbstate[SDLK_d])
+					(EV_KEY(ev) == SDLK_d && kbstate[SDLK_s]) || (EV_KEY(ev) == SDLK_s && kbstate[SDLK_d])
 #else
-					ev.key.keysym.sym == SDLK_e
+					EV_KEY(ev) == SDLK_e
 #endif
 					) {
 				enable_screenshake = !enable_screenshake;
@@ -594,8 +608,8 @@
 //lots of code from https://github.com/SDL-mirror/SDL/blob/bc59d0d4a2c814900a506d097a381077b9310509/src/video/SDL_surface.c#L625
 //coordinates should be scaled already
 static inline void Xblit(SDL_Surface* src, SDL_Rect* srcrect, SDL_Surface* dst, SDL_Rect* dstrect, int color, int flipx, int flipy) {
-	assert(src && dst && !src->locked && !dst->locked);
-	assert(dst->format->BitsPerPixel == 32 && src->format->BitsPerPixel == 8);
+	assert(src && dst && !SURFACE_LOCKED(src) && !SURFACE_LOCKED(dst));
+	assert(SURFACE_BITSPP(dst) == 32 && SURFACE_BITSPP(src) == 8);
 	SDL_Rect fulldst;
 	/* If the destination rectangle is NULL, use the entire dest surface */
 	if (!dstrect)
@@ -637,7 +651,9 @@
 
 	/* clip the destination rectangle against the clip rectangle */
 	{
-		SDL_Rect *clip = &dst->clip_rect;
+		SDL_Rect cliprc;
+		SURFACE_CLIP(dst, &cliprc);
+		SDL_Rect *clip = &cliprc;
 		int dx, dy;
 
 		dx = clip->x - dstrect->x;
@@ -1051,11 +1067,22 @@
 		tries_left--;
 
 		//use first available controller
+#if SDL_MAJOR_VERSION >= 3
+		int count = 0;
+		SDL_JoystickID* gamepads = SDL_GetGamepads(&count);
+		SDL_JoystickID first_gamepad = gamepads && count > 0 ? gamepads[0] : 0;
+		SDL_free(gamepads);
+		printf("sdl reports %i controllers\n", count);
+		for (int i = 0; i < count; i++) {
+			if (first_gamepad) {
+				controller = SDL_OpenGamepad(first_gamepad);
+#else
 		int count = SDL_NumJoysticks();
 		printf("sdl reports %i controllers\n", count);
 		for (int i = 0; i < count; i++) {
 			if (SDL_IsGameController(i)) {
 				controller = SDL_GameControllerOpen(i);
+#endif
 				if (!controller) {
 					fprintf(stderr, "error opening controller: %s\n", SDL_GetError());
 					return;
