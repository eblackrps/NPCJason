## Highlights

- Expanded personality states so Jason feels moodier, smugger, busier, sneakier, and more intentionally confused.
- Smarter desktop movement with pacing, hesitation, edge inspection, and safer recovery around screen boundaries.
- Reusable gag chains and mini-scenarios, including Busy IT Morning, Homelab Troubleshooting, Network Victory Lap, Responsible Adult Moment, and Office Chaos.
- Favorites and taste-shaping that bias skins, toys, scenarios, and quote packs without flattening the randomness.
- Discoveries and unlockables, including Astronaut Jason and longer-session surprises.
- Seasonal and special-event support with manual override for modes like Monday Morning Survival, Patch Day Panic, and Homelab Weekend.
- Richer optional audio behavior with category-aware mute handling and quick mute control from the tray.
- Stronger persistence for mute state, favorites, unlocks, enabled packs, special modes, and continuity between launches.
- New "what do" sayings folded into the structured quote-pack system.

## Fixes And Polish

- Fixed unlock logic so normal content stays available while true discovery content unlocks correctly.
- Fixed speech sound playback to respect the speech sound category instead of bypassing mute/category rules.
- Fixed scripted movement focus so edge/corner inspection beats land where the scenario asked them to.
- Hid locked scenarios from normal tray selection until they are actually discovered.
- Fixed packaged builds to load bundled resources from the frozen app directory without duplicate skin/pack overrides.
- Hardened toy startup so missing UI support fails safely during headless validation.
- Improved installer and run/build scripts so they work cleanly with `py`-based Python installs and local-user Inno Setup installs.
