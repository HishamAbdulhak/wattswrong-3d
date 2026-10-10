# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

The import above is the canonical guide: app architecture, data contract, conventions, issue tracker. Below are only the working notes that it doesn't cover.

## Commands

There is no build, lint or test suite. The whole app is `index.html`.

```bash
npx serve .                      # or: python3 -m http.server 8000
cd backend && uv run --locked python -m pipeline.embed   # validates the exports, re-embeds; asserts every row is kept
```

Syntax-check the module after editing (catches a broken minified line before a browser does):

```bash
python3 -c "import re;h=open('index.html').read();open('/tmp/mod.mjs','w').write(re.search(r'<script type=\"module\">(.*?)</script>',h,re.S).group(1))" && node --check /tmp/mod.mjs
```

## Working in `index.html`

- Lines 43–44 are the embedded `wattswrong-data` (~140 KB) and `wattswrong-series` (~1.4 MB) JSON on single lines. Never print or grep them whole. Read the data with `json.loads` on the matching `<script>` tag instead.
- Script lines run to ~3,000 characters. Edit them with exact-substring replacements that assert exactly one match. Locate functions with `grep -n 'function name('` and read single lines with `sed -n 'Np'`. Don't read the file linearly.
- `Data.load` runs at module top, before the three.js `await import`. Scene code can therefore read `Data` while it builds. After `WattsWrong.load`, `reinitialize()` must rebind anything the scene captured from the old data.

## Verifying changes

Verification is manual in a browser via `window.WattsWrong`. A reliable way to prove "nothing a householder sees changes":

1. Copy the original `index.html` (e.g. from `git show HEAD:index.html`) and serve it next to the edited one.
2. In both, collect `getState()`, `#meters` innerHTML, `.lane-label` text, `#anchors` labels, `#dash-content` for every meter (click the `#meters` buttons), and the `#recap` slides. Compare the results.
3. Interiors: click a home's anchor twice to enter it, then list the `#anchors` aria-labels.

Table-only mode: serve a copy whose importmap `"three"` URL points somewhere unreachable; the page must show the "3D view couldn't start" notice and the table, timeline and dashboards must still work. Headless Chromium `--dump-dom` works on that copy over `file://`, but hangs on the full 3D page because of the render loop.
