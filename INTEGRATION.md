# Seamless integration

Target: a Windows build of Awakenchan's engine with all of visy's seamless co-op,
native WPF launcher controls, and the game at
`E:\games\bloodborne seamless\gamedir\CUSA03173`.

## Source baselines

- Launcher and engine patch: Awakenchan/BloodBorneButPc
  `f3dcca13da2c2c81d2b9904dd549277e876e19e6`.
- Engine starting point: DarkIzuku/bloodborne_pc
  `8ecba9a4abdd54747e31d7fee54982e422b5f8e2`
  (`v0.4.0-darkizuku-preview.1`), with Awakenchan's published engine patch applied.
- Seamless: visy/bloodborne_pc_windows_port
  `ae113015554722e7e150e93c30060784694136ab` (`v0.6.5`).

Awakenchan's latest published engine source commit is labeled 0.9.29; the installed
package is 0.9.34-beta.3. Reconcile release changes available in shipped scripts and
release notes, and report any binary-only differences that cannot be reproduced.

## Implementation sequence

1. Import the reconstructed engine into this fork with pinned submodules and
   source provenance. Establish its CLANG64 build and baseline tests.
2. Integrate the complete party and serverless networking modules, routing guest
   network imports to them in party mode. Retain the original online path for its
   own sessions and preserve the renderer, shaders and performance optimizations.
3. Reconcile hook ownership, ABI/runtime helpers, main-thread callbacks, save
   isolation and recovery, input, messages and in-game party controls.
4. Add seamless mode, host/join credentials, party rules, connection/status and
   save-management controls to the WPF launcher. Configure fork-owned updates.
5. Run the imported logic/network/security tests and regression tests for the base
   engine, then validate solo and local multi-instance gameplay.
6. Package a self-contained test build, configured for the existing game dump,
   with isolated user data and clear logs. Record remaining tests needing a second
   physical PC. Do not claim those checks were completed locally.

## Progress

- GitHub fork created; working branch: `seamless-integration`.
- Published engine patch checked and applied in a separate reference checkout.
- Reference baseline: 24 selected Python tests passed.
- Exact hook collision identified at image offset `0x2034770`.
- CLANG64 dependencies are being installed from the base engine's build manifest.
- Game data and existing installations/saves remain untouched.
