---
name: bevy-video-capture
description: >
  Records a Bevy 0.20 scene frame by frame into PNGs and encodes them as an MP4, GIF or WebP:
  a fixed animation clock, one screenshot in flight, 2x output size, seamless loops and a frame
  checker. Use for "record my Bevy game to a video", a README GIF, a looping clip or trailer
  footage, frame-by-frame export, or captured frames that come out black, missing or doubled.
  Not for ECS, gameplay or system-order bugs (use bevy-ecs) or for publishing a store page
  trailer (steam-publish, itch-publish).
---

# Bevy Video Capture

Turn a running Bevy scene into clean footage. The scene is drawn as a function of a frame
number instead of wall time, every frame is saved as a PNG, a checker confirms nothing is
missing or blank, and a standard encoder makes the video. New code targets **Bevy 0.20**;
the screenshot API lives in `bevy::render::view::screenshot`.

## When to use

- Exporting a gameplay moment, a menu animation or a procedural scene as an MP4, GIF or
  WebP for a README, docs, social post or trailer edit.
- Making a clip that loops with no visible jump.
- Fixing captures that are black, skip frames, repeat frames or come out at the wrong size.

**When not to use:** live screen recording for streams (use OBS or the OS recorder), editing or
cutting a trailer, and ECS design questions (`bevy-ecs`). Uploading the result to a store page
belongs to `steam-publish` or `itch-publish`.

## Workflow

1. **Read the pinned version.** Check `Cargo.lock` for the resolved `bevy`. The pattern below
   is 0.20 code; older releases spell the screenshot API differently.
2. **Drive animation from a clock resource, not `Time`.** Every animated system reads
   `Res<Clock>`. While recording, the clock is `frame / fps`; in normal runs it follows
   `Time`. Wall time keeps moving while a screenshot is read back, so animation that reads
   `Time` skips or repeats poses in the output.
3. **Add the recorder plugin** (pattern below): fixed window size, a warm-up, one screenshot
   in flight, and the clock advancing only when the previous capture is done.
4. **Choose length and size.** Frames = seconds × fps. For a loop of `L` seconds record
   `L * fps` frames, numbered 0 to `L * fps - 1`; frame `L * fps` would equal frame 0. For
   1080p from a 960×540 layout, keep the layout and set the scale factor to 2.
5. **Record:** `cargo run --release -- --record frames`. Keep the window visible.
6. **Check the frames** (run from this skill's folder; paths are relative to it):
   `python scripts/check_frames.py path/to/frames --expect N`. A pass prints
   `Summary: 0 errors` and exits 0. On `blank-frames` or `missing-frames`, re-record from
   the first bad frame (resume pattern below) and check again. Add `--strict` to fail on
   stalled-clock and loop-seam warnings too.
7. **Encode** with one of the commands below, then ask the user to play the file and report
   whether motion, colours and the loop point look right.

## Patterns

### Recorder plugin (Bevy 0.20)

```rust
use bevy::{
    prelude::*,
    render::view::screenshot::{Capturing, Screenshot, save_to_disk},
    window::{WindowLevel, WindowResolution},
};
use std::path::PathBuf;

/// Animation time in seconds. Systems read this instead of `Time`.
#[derive(Resource, Default)]
pub struct Clock {
    pub t: f32,
}

#[derive(Resource)]
struct Recording {
    dir: PathBuf,
    fps: u32,
    frames: u32,
    warmup: u32, // updates to skip while pipelines compile
    update: u32,
    frame: u32, // next frame to capture; start above 0 to resume
}

pub struct RecorderPlugin {
    pub dir: Option<PathBuf>, // None = normal interactive run
    pub seconds: f32,
    pub fps: u32,
    pub scale: f32, // 2.0 renders the 960x540 layout at 1920x1080
    pub resume_at: u32,
}

impl Plugin for RecorderPlugin {
    fn build(&self, app: &mut App) {
        let recording = self.dir.is_some();
        app.add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                resolution: WindowResolution::new(
                    (960.0 * self.scale) as u32,
                    (540.0 * self.scale) as u32,
                )
                .with_scale_factor_override(self.scale),
                resizable: false,
                // A covered window can stop presenting; keep it on top while recording.
                window_level: if recording { WindowLevel::AlwaysOnTop } else { WindowLevel::Normal },
                ..default()
            }),
            ..default()
        }))
        .init_resource::<Clock>();

        if let Some(dir) = self.dir.clone() {
            std::fs::create_dir_all(&dir).expect("create the frames folder");
            app.insert_resource(Recording {
                dir,
                fps: self.fps,
                frames: (self.seconds * self.fps as f32).round() as u32,
                warmup: 90,
                update: 0,
                frame: self.resume_at,
            })
            .add_systems(First, |rec: Res<Recording>, mut clock: ResMut<Clock>| {
                clock.t = rec.frame as f32 / rec.fps as f32;
            })
            .add_systems(Last, capture);
        } else {
            let period = self.seconds;
            app.add_systems(First, move |time: Res<Time>, mut clock: ResMut<Clock>| {
                clock.t = time.elapsed_secs() % period;
            });
        }
    }
}

fn capture(
    mut commands: Commands,
    mut rec: ResMut<Recording>,
    pending: Query<(), Or<(With<Screenshot>, With<Capturing>)>>,
    mut exit: MessageWriter<AppExit>,
) {
    rec.update += 1;
    // Wait out the warm-up, and keep at most one screenshot in flight.
    if rec.update <= rec.warmup || !pending.is_empty() {
        return;
    }
    if rec.frame < rec.frames {
        let path = rec.dir.join(format!("frame-{:04}.png", rec.frame));
        commands
            .spawn(Screenshot::primary_window())
            .observe(save_to_disk(path));
        rec.frame += 1; // the clock moves on only after this capture is queued
    } else {
        exit.write(AppExit::Success); // no screenshot is still in flight
    }
}
```

The screenshot entity is despawned after its image is read back, so an empty `pending`
query means the previous frame has been captured. The clock then moves one frame, and the
next update renders and captures that frame.

### Seamless loops

Give every motion a whole number of cycles per loop of `L` seconds:

```rust
let phase = std::f32::consts::TAU * clock.t / LOOP; // one turn per loop
let angle = start + phase * turns as f32;          // turns: integer
let x = base_x - (speed * clock.t) % period;        // scrolling: speed * LOOP == period
```

A wheel rolling on a scrolling road needs `speed * LOOP / radius` to be a multiple of the
angle between spokes. Random layouts use a fixed seed so every run places things the same way.

### Encode

```bash
# MP4 for browsers and social: H.264, yuv420p, even width and height
ffmpeg -framerate 30 -i frames/frame-%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 out.mp4
# Looping GIF with a palette built from the clip
ffmpeg -framerate 25 -i frames/frame-%04d.png -vf "scale=720:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 out.gif
# Looping WebP: smaller than GIF and keeps glow and gradients
ffmpeg -framerate 25 -i frames/frame-%04d.png -vf scale=720:-1 -c:v libwebp -loop 0 -q:v 75 out.webp
```

Without ffmpeg, Pillow can write GIF and WebP (`Image.save(..., save_all=True, loop=0)`), and
on macOS AVFoundation's `AVAssetWriter` can write H.264.

## Gotchas

- **Frames turn black partway through a long capture, often on macOS** → the window stopped
  presenting (covered by another window, or after a long run), so the swapchain image is
  empty. Keep `WindowLevel::AlwaysOnTop` and the window visible; when the checker reports
  `blank-frames`, delete from the first blank frame and resume with `frame` starting there.
- **Output is 1920×1080 or 3840×2160 when you wanted 960×540** → the window's scale factor
  multiplies the physical size on HiDPI screens. Set `with_scale_factor_override` to the
  factor you want; it keeps the layout and scales the pixels.
- **The first frames are empty or missing meshes and text** → shaders and pipelines compile
  during the first frames. Skip a warm-up of updates before the first capture.
- **Black or skipped frames in heavy scenes (bloom, high resolution)** → screenshots were
  requested every update and piled up in GPU readback. Keep one in flight, as above.
- **The checker warns `stalled-clock`** → an animated system reads `Time`, or the clock
  advanced from wall time. Read `Res<Clock>` everywhere that moves.
- **A visible jump where the loop restarts** → one motion is not a whole number of cycles
  per loop, or the last frame equals the first (`loop-seam` warning). Fix the cycle counts
  or drop the extra frame.
- **The app exits and the last frame file is missing** → it quit while a screenshot was
  still in flight. Exit only when the `pending` query is empty.
- **The MP4 will not play in a browser or on a phone** → it was encoded as yuv444 or has an
  odd width or height. Use `-pix_fmt yuv420p` and even dimensions.
- **GIF shows colour bands around glows** → GIF has 256 colours per frame. Use WebP or MP4
  for bloom and gradients, or build a palette with `palettegen` as above.

## Related skills

- `bevy-ecs` — systems, schedules and the headless tests for the scene being recorded.
- `steam-publish`, `itch-publish` — where trailer footage usually ends up.

## Version notes

Last verified: 2026-11-17.

- Bevy 0.20.1: `Screenshot::primary_window`, `save_to_disk`, `Capturing`,
  `WindowResolution::with_scale_factor_override` and `WindowLevel::AlwaysOnTop` are the 0.20
  names. The recorder pattern was compiled and used to record three scenes (2D shapes, 4,000
  entities with bloom, 3,600 particles with `Text2d`) at 960×540 and 1920×1080, 20–30 fps, on
  macOS with Metal and Rust 1.97.1. Windows and Linux capture was not exercised.
- `scripts/check_frames.py` was run on those recordings and on frames with gaps, blank RGB and
  RGBA frames, duplicates and a repeated loop frame.
- Encoding was verified with Pillow (animated WebP) and AVFoundation (H.264 MP4). The ffmpeg
  commands above use standard libx264, palettegen and libwebp options but were not run in
  this verification.
- Sources: [screenshot example](https://github.com/bevyengine/bevy/blob/v0.20.1/examples/window/screenshot.rs),
  [Bevy 0.20 release notes](https://bevy.org/news/bevy-0-20/),
  [ffmpeg libx264 guide](https://trac.ffmpeg.org/wiki/Encode/H.264).
