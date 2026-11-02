/*
 * SDL3 and SDL3_mixer support for ccleste.
 *
 * sdl12main.c uses the SDL 1.2 and SDL_mixer 2 interfaces. As
 * sdl20compat.inc.c does for SDL2, this file maps the parts it uses to
 * SDL3 and to the track interface of SDL3_mixer.
 * Origin: EmberBSD (AI-assisted).
 */
#include <assert.h>

enum {
  SDL_SWSURFACE = 0,
  SDL_PHYSPAL = 1,
  SDL_LOGPAL = 2,
  SDL_SRCCOLORKEY = 4,
  SDL_HWPALETTE = 8,
};

#define SDL_INIT_OK(r) (r)
#define SURFACE_BITSPP(s) SDL_BITSPERPIXEL((s)->format)
#define SURFACE_BYTESPP(s) SDL_BYTESPERPIXEL((s)->format)
#define SURFACE_MAPRGB(s, r, g, b) SDL_MapSurfaceRGB((s), (r), (g), (b))
#define SURFACE_LOCKED(s) (((s)->flags & SDL_SURFACE_LOCKED) != 0)
#define SURFACE_CLIP(s, rc) SDL_GetSurfaceClipRect((s), (rc))
#define EV_KEY(ev) ((ev).key.scancode)

static SDL_Surface* ccleste_CreateRGBSurface(Uint32 flags, int w, int h, int depth,
    Uint32 rmask, Uint32 gmask, Uint32 bmask, Uint32 amask) {
  (void)flags;
  SDL_PixelFormat format = depth == 8 ? SDL_PIXELFORMAT_INDEX8 :
      SDL_GetPixelFormatForMasks(depth, rmask, gmask, bmask, amask);
  SDL_Surface* surf = SDL_CreateSurface(w, h, format);
  if (surf && depth == 8 && !SDL_CreateSurfacePalette(surf)) {
    SDL_DestroySurface(surf);
    surf = NULL;
  }
  return surf;
}
#define SDL_CreateRGBSurface ccleste_CreateRGBSurface

static SDL_Surface* sdl3_screen = NULL;
static SDL_Texture* sdl3_screen_tex = NULL;
static SDL_Window* sdl3_window = NULL;
static SDL_Renderer* sdl3_rendr = NULL;
static SDL_Surface* SDL_SetVideoMode(int width, int height, int bpp, Uint32 flags) {
  (void)flags;
  if (!sdl3_window) {
    if (!SDL_CreateWindowAndRenderer("", width, height, SDL_WINDOW_RESIZABLE, &sdl3_window, &sdl3_rendr))
      return NULL;
    SDL_SetRenderLogicalPresentation(sdl3_rendr, width, height, SDL_LOGICAL_PRESENTATION_LETTERBOX);
    sdl3_screen_tex = SDL_CreateTexture(sdl3_rendr, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_STREAMING, width, height);
    if (!sdl3_screen_tex) {
      SDL_DestroyRenderer(sdl3_rendr);
      SDL_DestroyWindow(sdl3_window);
      sdl3_rendr = NULL;
      sdl3_window = NULL;
      return NULL;
    }
  }
  sdl3_screen = SDL_CreateSurface(width, height, SDL_PIXELFORMAT_RGBA32);
  assert(sdl3_screen && SDL_BITSPERPIXEL(sdl3_screen->format) == bpp);
  return sdl3_screen;
}
static void SDL_SetPalette(SDL_Surface* surf, int flag, SDL_Color* pal, int begin, int count) {
  (void)surf;
  (void)flag;
  (void)pal;
  (void)begin;
  (void)count;
}
static void SDL_WM_SetCaption(const char* title, const char* icon) {
  assert(sdl3_window != NULL);
  SDL_SetWindowTitle(sdl3_window, title);
  (void)icon;
}
static int SDL_WM_ToggleFullScreen(SDL_Surface* screen) {
  assert(screen == sdl3_screen);
  assert(sdl3_window != NULL);
  static bool fullscreen = false;
  fullscreen = !fullscreen;
  return SDL_SetWindowFullscreen(sdl3_window, fullscreen);
}
static SDL_Surface* SDL_GetVideoSurface(void) {
  return sdl3_screen;
}
static void SDL_Flip(SDL_Surface* screen) {
  assert(screen == sdl3_screen);
  assert(sdl3_window != NULL);
  SDL_UpdateTexture(sdl3_screen_tex, NULL, screen->pixels, screen->pitch);
  SDL_SetRenderDrawColor(sdl3_rendr, 0, 0, 0, 255);
  SDL_RenderClear(sdl3_rendr);
  SDL_RenderTexture(sdl3_rendr, sdl3_screen_tex, NULL, NULL);
  SDL_RenderPresent(sdl3_rendr);
}
static void ccleste_ShowCursor(int toggle) {
  if (toggle) SDL_ShowCursor();
  else SDL_HideCursor();
}
#define SDL_ShowCursor(toggle) ccleste_ShowCursor(toggle)

/* The keyboard state is indexed by scancodes, so use those constants. */
#define SDL_GetKeyState(n) ((const Uint8*)SDL_GetKeyboardState(n))
#undef SDLK_F9
#undef SDLK_ESCAPE
#undef SDLK_DELETE
#undef SDLK_F11
#undef SDLK_LSHIFT
#undef SDLK_LEFT
#undef SDLK_RIGHT
#undef SDLK_UP
#undef SDLK_DOWN
#undef SDLK_5
#undef SDLK_s
#undef SDLK_d
#undef SDLK_c
#undef SDLK_x
#undef SDLK_n
#undef SDLK_a
#undef SDLK_b
#undef SDLK_z
#undef SDLK_e
#undef SDLK_v
#define SDLK_F9 SDL_SCANCODE_F9
#define SDLK_ESCAPE SDL_SCANCODE_ESCAPE
#define SDLK_DELETE SDL_SCANCODE_DELETE
#define SDLK_F11 SDL_SCANCODE_F11
#define SDLK_LSHIFT SDL_SCANCODE_LSHIFT
#define SDLK_LEFT SDL_SCANCODE_LEFT
#define SDLK_RIGHT SDL_SCANCODE_RIGHT
#define SDLK_UP SDL_SCANCODE_UP
#define SDLK_DOWN SDL_SCANCODE_DOWN
#define SDLK_5 SDL_SCANCODE_5
#define SDLK_s SDL_SCANCODE_S
#define SDLK_d SDL_SCANCODE_D
#define SDLK_c SDL_SCANCODE_C
#define SDLK_x SDL_SCANCODE_X
#define SDLK_n SDL_SCANCODE_N
#define SDLK_a SDL_SCANCODE_A
#define SDLK_b SDL_SCANCODE_B
#define SDLK_z SDL_SCANCODE_Z
#define SDLK_e SDL_SCANCODE_E
#define SDLK_v SDL_SCANCODE_V

/*
 * SDL_mixer 2 interface on SDL3_mixer tracks: one track plays the music,
 * a pool of tagged tracks plays the sound effects.
 */
#define MIX_INIT_OGG 0x00000010
#define CCLESTE_SFX_TRACKS 8
#define CCLESTE_SFX_TAG "ccleste-sfx"
typedef MIX_Audio Mix_Chunk;
typedef MIX_Audio Mix_Music;
static MIX_Mixer* ccleste_mixer = NULL;
static MIX_Track* ccleste_music = NULL;
static MIX_Track* ccleste_sfx[CCLESTE_SFX_TRACKS];

#define Mix_GetError SDL_GetError
static int Mix_Init(int flags) {
  return MIX_Init() ? flags : 0;
}
static void Mix_Quit(void) {
  MIX_Quit();
}
static int Mix_OpenAudio(int frequency, SDL_AudioFormat format, int channels, int chunksize) {
  SDL_AudioSpec spec = { format, channels, frequency };
  (void)chunksize;
  ccleste_mixer = MIX_CreateMixerDevice(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec);
  if (!ccleste_mixer) return -1;
  ccleste_music = MIX_CreateTrack(ccleste_mixer);
  if (!ccleste_music) return -1;
  for (int i = 0; i < CCLESTE_SFX_TRACKS; i++) {
    ccleste_sfx[i] = MIX_CreateTrack(ccleste_mixer);
    if (!ccleste_sfx[i] || !MIX_TagTrack(ccleste_sfx[i], CCLESTE_SFX_TAG)) return -1;
  }
  return 0;
}
static void Mix_CloseAudio(void) {
  if (ccleste_mixer) MIX_DestroyMixer(ccleste_mixer);
  ccleste_mixer = NULL;
  ccleste_music = NULL;
  for (int i = 0; i < CCLESTE_SFX_TRACKS; i++) ccleste_sfx[i] = NULL;
}
static Mix_Chunk* Mix_LoadWAV(const char* path) {
  return MIX_LoadAudio(ccleste_mixer, path, true);
}
static Mix_Music* Mix_LoadMUS(const char* path) {
  return MIX_LoadAudio(ccleste_mixer, path, false);
}
#define Mix_FreeChunk MIX_DestroyAudio
#define Mix_FreeMusic MIX_DestroyAudio

static int Mix_PlayChannel(int channel, Mix_Chunk* chunk, int loops) {
  (void)channel;
  (void)loops;
  for (int i = 0; i < CCLESTE_SFX_TRACKS; i++) {
    MIX_Track* track = ccleste_sfx[i];
    if (!track || MIX_TrackPlaying(track) || MIX_TrackPaused(track)) continue;
    if (!MIX_SetTrackAudio(track, chunk) || !MIX_PlayTrack(track, 0)) return -1;
    return i;
  }
  return -1;
}
static void Mix_HaltChannel(int channel) {
  (void)channel;
  if (ccleste_mixer) MIX_StopTag(ccleste_mixer, CCLESTE_SFX_TAG, 0);
}
static void Mix_Pause(int channel) {
  (void)channel;
  if (ccleste_mixer) MIX_PauseTag(ccleste_mixer, CCLESTE_SFX_TAG);
}
static void Mix_Resume(int channel) {
  (void)channel;
  if (ccleste_mixer) MIX_ResumeTag(ccleste_mixer, CCLESTE_SFX_TAG);
}

static int Mix_FadeInMusic(Mix_Music* music, int loops, int ms) {
  if (!ccleste_music || !MIX_SetTrackAudio(ccleste_music, music)) return -1;
  SDL_PropertiesID options = SDL_CreateProperties();
  if (!options) return -1;
  SDL_SetNumberProperty(options, MIX_PROP_PLAY_LOOPS_NUMBER, loops);
  if (ms > 0) SDL_SetNumberProperty(options, MIX_PROP_PLAY_FADE_IN_MILLISECONDS_NUMBER, ms);
  bool played = MIX_PlayTrack(ccleste_music, options);
  SDL_DestroyProperties(options);
  return played ? 0 : -1;
}
static int Mix_PlayMusic(Mix_Music* music, int loops) {
  return Mix_FadeInMusic(music, loops, 0);
}
static int Mix_FadeOutMusic(int ms) {
  if (!ccleste_music) return 0;
  return MIX_StopTrack(ccleste_music, ms > 0 ? MIX_TrackMSToFrames(ccleste_music, ms) : 0);
}
static void Mix_HaltMusic(void) {
  if (ccleste_music) MIX_StopTrack(ccleste_music, 0);
}
static void Mix_PauseMusic(void) {
  if (ccleste_music) MIX_PauseTrack(ccleste_music);
}
static void Mix_ResumeMusic(void) {
  if (ccleste_music) MIX_ResumeTrack(ccleste_music);
}
