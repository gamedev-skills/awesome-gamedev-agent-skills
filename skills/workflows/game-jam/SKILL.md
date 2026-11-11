---
name: game-jam
description: >
  Plans and ships a game jam entry against a fixed deadline: reads the jam rules, scopes to the
  clock, keeps a cut list and checks the build before submitting. Use for Ludum Dare, GMTK, Global
  Game Jam or any itch.io jam, a 48-hour game, or "we're behind, what do we cut". Not for untimed
  experiments (`prototype-fast`) or upload commands (`itch-publish`).
---

# Game Jam

Turn a theme and a fixed deadline into a submitted, playable game. The win condition is a
build that is attached to the jam before it closes, not the game first imagined. The agent
keeps the plan in a file, builds the smallest loop first, cuts on schedule, and runs the build
checks itself; the user decides the concept, plays the build and presses submit.

## When to use

- Entering a timed jam, scoping a 48- to 96-hour or one-week build, deciding what to cut to hit
  a deadline, or getting a jam entry submitted.

**Not for:** the core loop's engine code (engine skills such as `godot-2d-movement` or
`phaser-core`, or genre skills such as `platformer`); experiments with no deadline
(`prototype-fast`); a commercial release (`steam-publish`, `itch-publish`).

## Workflow

1. **Get the rules before the theme drops.** Ask the user for the jam page URL and read it (or
   ask them to paste the rules). Record in `JAM.md` at the project root: length, theme reveal
   time, submission deadline in UTC and the user's local time, team and asset rules, the
   generative-AI rule, required platforms, where the entry is submitted, whether uploads lock
   during rating, and whether rating others matters. Each of these has disqualified finished
   games. Recurring jams' current rules are summarised in Version notes; the live page wins.
2. **Prep what the rules allow in advance:** an empty project that exports, input and a
   title/end screen stub, an export command that has run once, and licensed font and SFX
   sources. Day-one hours are too precious for this.
3. **Theme to one sentence.** Offer about ten ideas quickly, then help the user commit to one
   that fits *"You [verb] to [goal] while [constraint]."* If it does not fit one sentence, it is
   too big. Write it in `JAM.md`.
4. **Scope to the clock.** Use the budget table (Pattern 1): one core mechanic, one hook,
   everything else on a stretch list in `JAM.md`.
5. **Build the vertical slice first:** start, play, win or lose, restart, with primitives. A
   complete tiny loop beats a half-built big one.
6. **Check in against the timeline** (Pattern 2) at each block boundary. When the loop is late,
   cut from the stretch list using the triage rules (Pattern 3) and log the cut in `JAM.md`.
7. **Reserve the last ~20% of the clock for shipping:** export, run the Verify checks, capture
   screenshots, write the page. Builds tend to break in the last hours.
8. **Submit early, then update while allowed.** Upload a working build well before the
   deadline. After the deadline many jams lock uploads or allow only declared bug fixes, so
   the build attached at the deadline is the one people rate.

## Patterns

### 1. Scope budget by jam length (plan backwards from the deadline)

```text
              | 48-hour jam            | 72-96 hour jam        | 1-week jam
--------------|------------------------|-----------------------|------------------------
Core mechanic | 1, proven by hour 6    | 1-2                   | 2-3 interacting
Levels/content| 1 hand-made or gen'd   | 3-5                   | 8-12 + progression
Art           | placeholder/1 palette  | cohesive 1-artist set | themed set + UI
Audio         | 3-5 SFX + 1 loop       | SFX + 1-2 tracks      | adaptive music
SHIP BUFFER   | last 8-10 h            | last 12-16 h          | last full day
```

### 2. The 48-hour timeline

```text
H0-2    Lock the one-sentence concept; name the core mechanic and win/lose.
H2-8    Core loop with primitives. Playable, no art.
H8-12   Sleep. Tired code is tomorrow's bug list.
H12-24  One level or encounter, tune difficulty, add the hook.
H24-30  Sleep; the user plays the build (and ideally one other person); cut what isn't landing.
H30-38  Art and audio pass, then juice (see `game-feel`).
H38-44  Feature freeze: fix only crashes and soft-locks.
H44-48  Export, Verify, screenshots, page, SUBMIT by about H46.
```

### 3. Feature triage

```text
For every feature, in order:
  1. Does the core loop work without it?  -> yes: stretch goal, not MVP.
  2. Would a player notice it missing?    -> no: cut it.
  3. Is it under 30 minutes of work?      -> no: defer past the ship buffer.
Under deadline pressure the default is CUT; it can return in a post-jam version.
```

### 4. `JAM.md` skeleton

```text
Jam: <name + URL>     Deadline: <UTC> / <local>     Upload lock: yes/no
Rules: team | assets | AI | platforms | submit where
Concept: You <verb> to <goal> while <constraint>.
MVP: <core mechanic>, <hook>, start/play/end/restart
Stretch (in cut order): ...
Cut log: <hour> cut <feature> because <reason>
```

## Verify

Run these before submitting, on the exported build, not the editor:

1. **Export from the command line** with the engine skill's export path (for example
   `godot-export` or `unity-build-pipeline`) and confirm it exits 0.
2. **Clean-path test.** Zip the export, unzip it into a new temporary folder outside the
   project, and launch it there (or, for a web build, serve that folder on `127.0.0.1` and load
   it in a headless browser). Missing assets and wrong working directories show up only here.
   Read the log or browser console for errors.
3. **Package check.** List the zip: the executable or `index.html` at the top level, no
   project files, editor folders or debug symbols. For itch.io, run the `butler push
   --dry-run` check from `itch-publish`.
4. **Rules check.** Re-read the rules block in `JAM.md` against the build: platforms, controls
   (keyboard and mouse if required), credits and asset licences on the page, AI rule.
5. **Ask the user** to play the extracted build through once, start to restart, and report
   any soft-lock; then to submit and confirm the entry appears on the jam's entries page.
   Uploading to a game page alone does not enter it.

## Gotchas

- **Scope creep.** If the loop is not playable by the first third of the clock, cut now.
- **No ship buffer.** Exporting, zipping and writing the page takes 1 to 3 hours and usually
  surfaces a build bug. Treat the deadline as two hours earlier than it is.
- **Submitted to the page, not the jam.** On itch.io a jam entry is a separate submission from
  the jam page.
- **Fixing after the deadline.** Where uploads lock, the locked build is rated, and linking a
  "fixed" build elsewhere can disqualify the entry. Where fixes are allowed (Ludum Dare),
  fix bugs only and list the changes.
- **Untested export.** "Works in the editor" is not "works in the build."
- **Unlicensed or AI-made assets.** Web-scraped music, fonts or sprites can break jam rules and
  later distribution; credit every asset. AI rules differ sharply between jams: some
  disqualify AI art or audio, others only ask you to opt out of rating categories.
- **Polishing before the loop is fun.** Juice multiplies fun; it cannot create it.
- **Deadline time zone.** Jams state deadlines in one zone; GGJ sites use local time. Store
  both in `JAM.md`.

## References

- `prototype-fast`: read for greyboxing and the throwaway-vs-keep call before committing jam
  hours to a mechanic.
- `itch-publish`: read for the page, channels and `butler push` when the jam runs on itch.io.

## Related skills

- Engine cores (`phaser-core`, `love2d-core`, `godot-gdscript`, ...) and genre skills
  (`platformer`, `roguelike`, ...) build the loop the jam scopes around.

## Version notes

Last verified: 2026-11-11. Rules change between editions; read the live page for the edition
being entered.

- **Ludum Dare:** Compo is solo, 48 hours, all content made during the event, source code
  included. Jam is 72 hours, solo or team, any base code; third-party or older assets mean
  opting out of the matching categories. Each event ends with one Submission Hour for
  packaging; porting can follow. AI tools are allowed, but entries opt out of any category
  where a generator did most (about 90%) of the work. Entries live on ldjam.com and link to
  builds hosted elsewhere. The organiser has announced October 2028 as the last scheduled
  event.
- **GMTK Game Jam 2026** (itch.io, July 22 to 26, 2026): solo or team; must run on Windows or
  in a browser with keyboard or mouse; generative AI for art or audio, in the game or on the
  page, disqualifies the entry. Uploads lock for the five-day rating period, and linking to
  another build disqualifies. The web uploader takes files up to 1 GB; larger builds go
  through butler.
- **Global Game Jam 2027:** jam week January 25 to 31, 2027; sites run their own 48-hour window
  and deadline in local time. Teams choose their own licence and must upload an executable or
  a browser link; the policies page no longer requires source code, but the older "Upload your
  game" page still asks for it, so check your site's rules. No restriction on AI tools beyond
  the existing copyright and IP policies.
- Sources: [Ludum Dare rules](https://ldjam.com/events/ludum-dare/rules),
  [Ludum Dare AI FAQ](https://ludumdare.com/resources/questions/can-i-use-ai),
  [Ludum Dare end date (Game Developer)](https://www.gamedeveloper.com/production/ludum-dare-will-officially-end-in-october-2028),
  [GMTK Game Jam 2026](https://itch.io/jam/gmtk-jam-2026),
  [GGJ policies](https://globalgamejam.org/policies), [GGJ upload guide](https://globalgamejam.org/upload-your-game), [GGJ](https://globalgamejam.org/).
