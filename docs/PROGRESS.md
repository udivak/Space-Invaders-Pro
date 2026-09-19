# Space Invaders — Implementation Progress

Authoritative plan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
Plan version: 1.1 · Baseline commit: `23aa512e7e2bb9bf21f7648888d184b463bcff5f`.
Last updated: 2026-09-19.

## Current status

**Phases 1–6 implemented in the working tree; Phase 7 partially implemented; nothing committed.**
Branch `feature/space-invaders-overhaul` from baseline `23aa512`. Plan v1.1 was approved by an
independent Codex review (3 rounds, findings R1–R5 resolved) before implementation. Implementation by
Claude (Opus 5); independent code inspection by a fresh Codex session is recorded in the evidence below.

Automated evidence (2026-09-19, macOS, Python 3.13.7, Pygame 2.6.1 / SDL 2.28.4, pytest 8.3.5, dummy SDL
drivers): T0 baseline on a disposable copy: 14 passed. Final `python -m pytest -q`: 206 passed (run twice,
identical); `-m integration`: 13 passed. `scores.txt` SHA-256 unchanged before/after
(`4cd3e5a0…f6d9`). pyflakes clean.

Native smoke (macOS, Cocoa video driver, scripted events): `main.py` opened a real window, navigated menu ->
co-op -> gameplay and quit with exit 0; the captured frame rendered correctly and legacy scores migrated into
the scratch data root. CoreAudio was unavailable to that sandboxed shell, so the game started silently via the
audio-disabled path. Later launches from the same shell blocked inside `pygame.display.init()`.

Not evidenced: human keyboard play (M1/M2), real audio, hosted CI, the Windows candidate (B1) and playtests.
These remain PENDING for the owner.

## Status rules

- PLANNED: no implementation started.
- IN_PROGRESS: authorized work is active; acceptance not yet met.
- BLOCKED: a concrete prerequisite/decision prevents completion; explain it.
- DONE: required automated and manual acceptance for this task is evidenced.
- A missing environment/hardware check is PENDING evidence, never a pass.
- An investigation can conclude that evidence is unavailable; record that result explicitly and retain downstream native/release gates.
- External publication is a separate permission/status, not implied by local completion.

Update the relevant row plus an evidence entry. The plan owns design decisions; do not create a second roadmap here.

## Phase gates

| Phase | Gate | Status |
| --- | --- | --- |
| 1 | Stabilization — plan Section 6 | Automated gate met; native M1 PENDING |
| 2 | Structural Refactor — plan Section 7 | Automated gate met; M2 native PENDING |
| 3 | Core Systems Cleanup — plan Section 8 | Automated gate met |
| 4 | Testing & Reliability — plan Section 9 | Automated gate met; native observations PENDING |
| 5 | Gameplay Improvements — plan Section 10 | Automated gate met; playtests PENDING |
| 6 | UI / UX / Game Feel — plan Section 11 | Automated gate met; native visual/audio PENDING |
| 7 | Packaging & Portfolio Quality — plan Section 12 | PARTIAL: 7.1–7.2 implemented; 7.3–7.5 BLOCKED |

## Task tracking

Status IMPLEMENTED means automated acceptance is evidenced and code is in the working tree, uncommitted. It is not DONE while a required native check is PENDING.

| ID | Task | Status | Validation evidence |
| --- | --- | --- | --- |
| 1.1 | Isolate the existing test baseline | IMPLEMENTED | Root score test replaced by tests/test_persistence.py on temp paths; repo scores.txt hash asserted |
| 1.2 | Resolve projectile consumption exactly once | IMPLEMENTED | tests/test_combat.py B1/B5/B6/B13 cases |
| 1.3 | Resolve pickups and enemy contacts exactly once | IMPLEMENTED | tests/test_combat.py B2/B3/B4, contact priority, boss contact |
| 1.4 | Break the import cycle and make bootstrap explicit | IMPLEMENTED | Fresh-process import-order tests; missing image error; silent start without mixer |
| 1.5 | Reset mode and drain events once per active screen frame | IMPLEMENTED | 2->1->2 selection test; one event.get per frame in app.run |
| 1.6 | Unwind screens through one lifecycle dispatcher | IMPLEMENTED | Superseded directly by 2.4 frame loop; 20-cycle lifecycle with weakrefs; QUIT test |
| 1.7 | Make legacy score I/O explicit and bound the score view | IMPLEMENTED | Retry/Continue; no-op on failure; legacy writer retired by 3.6 (see deviations) |
| 1.8 | Make boss vertical movement continuous from spawn | IMPLEMENTED; visual check PENDING | tests/test_entities.py boss continuity at y=100/250/299 |
| 1.9 | Remove the ineffective package quota without inventing one | IMPLEMENTED | Seven replacement cycles, one active package |
| 2.1 | Extract a gameplay session with update and draw boundaries | IMPLEMENTED | space_invaders/gameplay.py; seeded determinism test |
| 2.2 | Move entities into the application package | IMPLEMENTED | Classes.py removed; no imports of Classes/main from package |
| 2.3 | Extract non-gameplay screens behind frame-level methods | IMPLEMENTED | tests/test_screens.py |
| 2.4 | Replace screen adapters with one application frame loop | IMPLEMENTED; M2 native PENDING | Both launchers from another CWD (subprocess, dummy drivers) |
| 3.1 | Centralize current tuning and player input mappings | IMPLEMENTED | settings.Balance/ControlBindings; heat clamp tests |
| 3.2 | Decouple simulation from rendering with a fixed step | IMPLEMENTED | 30/60/120 fps equivalence; stall cap |
| 3.3 | Centralize combat outcomes in the gameplay session | IMPLEMENTED | Feedback drained once |
| 3.4 | Extract deterministic wave and package generation | IMPLEMENTED | tests/test_waves.py |
| 3.5 | Define score records and separate resource and data paths | IMPLEMENTED | paths/scores tests |
| 3.6 | Migrate score storage safely and show ranked results | IMPLEMENTED | Migration, R3 failure->save->restart, R5 encodings, atomic/backup tests |
| 4.1 | Consolidate deterministic logic tests | IMPLEMENTED | All tests under tests/; integration marker |
| 4.2 | Exercise complete lifecycle and fresh-process startup | IMPLEMENTED; native M1/M2 PENDING | tests/test_application_flow.py |
| 4.3 | Investigate baseline feel audio and performance | CONCLUDED: evidence unavailable | No native display/audio in implementation environment; native observations PENDING |
| 5.1 | Replace unseen wave delays with a paced spawn schedule | IMPLEMENTED; playtest PENDING | modern-step1 behavior; ruleset now modern-v1 |
| 5.2 | Give the blue enemy one distinct movement pattern | IMPLEMENTED; playtest PENDING | Weave bounds/continuity/mean-lane tests |
| 5.3 | Add a signaled second boss firing phase | IMPLEMENTED; playtest PENDING | 201/200/196 HP, 72/96-tick timers, 15-tick telegraph |
| 5.4 | Give temporary pickups predictable lifetimes | IMPLEMENTED; playtest PENDING | 719/720 ticks, refresh, 3 charges, carryover |
| 5.5 | Reward boss clears and record a coherent co-op result | IMPLEMENTED; playtest PENDING | Boss bonus once; team score; frozen result |
| 6.1 | Make menus navigable and instructions complete | IMPLEMENTED; native visual PENDING | Keyboard focus/Tab/Enter/Escape tests; headless screenshots reviewed |
| 6.2 | Add pause restart and focus-loss handling | IMPLEMENTED | 10 s pause freeze, focus loss, restart, menu abandon |
| 6.3 | Make HUD and run results explain the state | IMPLEMENTED; native visual PENDING | Headless screenshots of HUD/results reviewed |
| 6.4 | Add restrained hit kill and pickup feedback | IMPLEMENTED; audio PENDING | Particle cap 96, separate RNG, reduced effects |
| 6.5 | Add small persistent audio and effects preferences | IMPLEMENTED; audio PENDING | Round trip, malformed, unwritable, no-audio |
| 7.1 | Make dependency installation and CI reproducible | IMPLEMENTED; hosted CI NOT RUN | requirements*.txt (UTF-8), .github/workflows/tests.yml (YAML parses) |
| 7.2 | Document the real game and its development workflow | IMPLEMENTED; owner license/provenance decisions PENDING | Readme.md, docs/ARCHITECTURE.md, docs/CREDITS.md |
| 7.3 | Build a reproducible Windows release candidate | BLOCKED | Spec, requirements-build.txt and docs/BUILD.md prepared; needs native Windows build and B1 |
| 7.4 | Clean the tracked repository after migration and packaging | BLOCKED | Depends on a validated 7.3 candidate |
| 7.5 | Prepare portfolio media and the final release handoff | BLOCKED | Depends on 7.4; publication separately unauthorized |

## Deviations from the plan

- No commits: commits were not authorized, so the per-task commit boundaries were not created. All work is
  one uncommitted working-tree change on branch `feature/space-invaders-overhaul` (plan suggested a
  `codex/` prefix; the builder was Claude).
- Because nothing was committed per task, the final architecture was written directly. Transitional bridges
  (1.4 runtime globals, 1.6 dispatcher, 1.7 paged raw legacy view and atomic legacy writer, 2.3 loop adapters)
  never existed as intermediate states. Their behaviors are covered by the final equivalents; the v1.1 legacy
  decoding rules (R1/R5) apply to migration and the read-only legacy view, and nothing rewrites scores.txt.
- Classic-v1 characterization traces were not recorded before Phase 5 changes, since the tree went straight
  to modern-v1 rules.
- Menu gained Scores, Settings and Quit entries to reach 3.6 and 6.5 screens by keyboard.
- Shield is drawn as a thin ring (plan allowed ring or texture); shield.png remains unused.
- Boss phase two: the first volley fires at the end of the 15-tick telegraph, then every 96 ticks.
- Spawn lanes: x = 50, 210, 370, 530, 690, 850; blue baselines clamped to [40, 840].

## Evidence log

- Plan review: Codex CLI 0.155.1 (model from user config, gpt-6-astra), isolated CODEX_HOME without MCP
  servers; round 1 REVISE (R1–R4), round 2 REVISE (R5), round 3 APPROVED; approval check matched plan SHA.
- Code inspection round 1 (fresh Codex session): REVISE with C1–C8; all accepted and fixed:
  strict CSV parsing (C1); unreadable legacy file reported instead of crashing Scores (C2); skipped legacy
  lines reported at startup and after a migrating save (C3); fatal boss contact ends the update before
  other outcomes (C4); the session Balance reaches every entity and projectile (C5); HUD text clamped to the
  viewport (C6); `__main__` guarded and included in inert-import tests (C7); scores.txt preservation checked
  across the whole test session (C8). Regression tests were added for each.
- Code inspection round 2 (fresh Codex session, final allowed round): C1–C8 not re-raised; five new
  medium findings, all accepted and fixed with regressions in tests/test_edge_cases.py: control characters
  in stored names/notices broke rendering (IR-01); focus loss in the same batch as a transition into
  gameplay did not pause, now tracked globally by App (IR-02); oversized/NaN numbers in settings.json
  crashed startup (IR-03); a legacy score too long for int() escaped migration (IR-04); new hit flashes were
  aged away before their first draw (IR-05). **These IR fixes have not been independently re-inspected**
  because the inspection budget was spent.
- Tests: see Current status. Headless screenshots of menu, instructions, gameplay (solo boss and co-op),
  pause, results with save error, Top 10 and settings were reviewed for layout.

## Evidence entry template

```text
Task ID and date:
Requested/authorized scope:
Starting commit and relevant working-tree changes:
Modified files:
Behavior preserved / intentionally changed:
Automated checks: exact command, exit code and summary
Manual checks: platform, scenario, observation
Data safety: temporary destinations and original-file checks
Native/audio/Windows/hosted checks still pending:
Focused re-review outcome:
Deviations or approved plan amendment:
Commit: actual hash, or not committed
Acceptance: met / unmet items
Next eligible task:
```

## Open evidence and release gates

| Item | Owner task | State / requirement |
| --- | --- | --- |
| Native solo/co-op feel and real audio | 4.3, 5.x, 6.4 | PENDING; headless evidence is insufficient |
| Asset provenance and owner code-license decision | 7.2 | PENDING; record unknowns, do not invent permission |
| Native Windows candidate parity | 7.3 | PENDING; current checked-in executable was not executed |
| Hosted CI matrix | 7.1 | NOT RUN |
| Safe migration of actual user history | 3.6 | IMPLEMENTED and tested on temp copies; original scores.txt retained unchanged |
| Release candidate | 7.3–7.5 | NOT BUILT |
| External publication | Separate user authorization | NOT AUTHORIZED by this planning request |

## Plan amendments

v1.1 (2026-09-19, from independent Codex plan review): R1/R2 legacy decoding and atomic legacy rewrite; R3 migration precondition before first save; R4 reverse-order Phase 5 rollback or fresh ruleset ID; R5 non-UTF-8 legacy encoding unconfirmed until SPACE_INVADERS_LEGACY_ENCODING.
