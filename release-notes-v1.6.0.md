## Highlights

- Added a lightweight companion framework and the first real sidekick: a pet mouse that idles, follows Jason, waits, reacts, and joins the desktop chaos without taking over the app.
- Added the Feed Cheese interaction with a readable backflip routine and the exact punchline `Ansible Chris made me do it`.
- Expanded dancing to three routines total so Jason rotates between distinct little victory bits instead of repeating the same move every time.
- Added Squarl Suit Jason as a proper first-class skin with full metadata, offsets, tray colors, and quote affinity.
- Added smarter app-title humor so Jason can occasionally react to useful foreground window titles without feeling invasive or constant.
- Added a dedicated Cisco joke pack for networking moments, Cisco-adjacent titles, and smug post-routing desktop energy.
- Tuned comedy/context biasing so companion moments, dances, title jokes, and the existing quote packs play together more cleanly.

## Fixes And Polish

- Fixed companion shutdown so the mouse window cleans up correctly when the app exits.
- Hardened title handling so empty or missing window titles do not break reactions, and generic titles no longer over-bias the quote system.
- Ensured the cheese/backflip gag can still land its final line instead of losing it to the normal ambient speech cooldown.
- Normalized selected companion persistence so bad saved values recover safely to a valid companion.
- Added validation coverage for the new title packs, companion-aware template tokens, tray snapshot state, and Squarl skin registration.
