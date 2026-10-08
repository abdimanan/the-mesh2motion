# Animation Lab: a Mesh2Motion animation library add-on for Blender

**Status:** In progress: AL1 done ([AL1](AL1-build-animation-library.md)), AL2 done ([AL2](AL2-thumbnails.md)); AL3 (add-on skeleton) next
**Date:** 2026-10-08
**Related:** [Mixamo FBX download for Blender](../../mesh2motion-app/docs/download%20animation%20as%20mixamo%20bone%20rig/) (the feature built before this)

## The idea

A Blender add-on called **Animation Lab** that works like **BlenderKit**, but for animations:

- a panel inside Blender showing the Mesh2Motion animation library as a grid of previews
- search and filter (skeleton type, category)
- **preview** an animation before using it
- **import the skeleton** (rig) into the scene with one click
- **apply** an animation to the selected armature, or push it into the **NLA Editor**

## Short answers

| Question | Answer |
|---|---|
| **A. Is it a good idea?** | **Yes.** The animations are CC0 (free to redistribute), already exist, and there's no good free "BlenderKit for animations". The main design choice is to keep it **simple and offline**: no accounts, no server. |
| **B. How much is ready?** | **About 35–40 %.** The content (251 animations, 9 rigs, previews) and the hard maths (Mixamo conversion) exist. The add-on itself, its UI and the build pipeline don't. |
| **C. What tech gets added?** | **Python + Blender's `bpy` API** (the add-on), Blender's **extension format** (`blender_manifest.toml`), a **build pipeline** reusing the existing **TypeScript/Node** code plus **Blender in headless mode**, and **GitHub** for hosting and CI. |
| **D. Can it be built for free?** | **Yes, completely**, as long as it stays an offline library without user accounts or uploads. Every tool and host listed below has a free option. |
| **E. How big compared to the Mixamo feature?** | **A full version is about 3–4× bigger. A first usable version (MVP) is about 1.5× bigger.** |

---

## A. What I think

### Why it's a good idea
1. **The content is ready and free to share.** The assets are **CC0**: anyone may copy, change and redistribute them, including inside an add-on. That's the hardest part of a library, and it's done.
2. **Blender users want this.** Getting animations into Blender today means downloading from a website, importing, renaming bones and fixing scale. We just spent 9 phases fixing exactly those problems for one export path. An add-on hides all of that.
3. **It can reuse what we built.** The Mixamo work (bone axes rule, animation converter, correct units and axes) is proven in Blender, so Animation Lab can offer **"apply to my Mixamo character"** on day one.
4. **There's a template.** The assets repo already ships a Blender extension (`mesh2motion-assets/motion-capture/blender-plugin/mocopi_m2m_retarget`): manifest, build script, sidebar panel, tests, about 3,400 lines of Python, GPL-3.0. Animation Lab can copy its structure.

### What to keep in mind
| Risk | Why it matters | How to handle it |
|---|---|---|
| **Video previews** | The library's previews are **MP4 files** (`static/animpreviews/*`, dark and light versions). Blender's UI can't play video in a panel. | Show a **still thumbnail** in the grid (rendered once at build time), and play the real animation on a temporary **preview armature in the viewport** when the user clicks it. |
| **Other rigs** | "Apply to *any* armature" means retargeting arbitrary skeletons, which is hard. | Start with skeletons we know exactly: the **Mesh2Motion rigs** and **Mixamo** (Y Bot-style) armatures. Add "map your own bones" later. |
| **Mixamo licensing** | Shipping Mixamo-derived data (`MixamoStandardSkeleton.ts`) inside a **publicly distributed** add-on is riskier than in a personal repo. | Don't ship it. Convert onto **the Mixamo armature the user already has in their scene** (select it, click Apply). Same exact result, no Mixamo data in the add-on. |
| **Blender API changes** | Blender 4.4 introduced layered/slotted actions; the old `action.fcurves` access is deprecated and goes away in Blender 5.0. | Write against the new action API from the start and test on the current LTS version plus the newest release. |
| **Name** | "Animation Lab" may already be used by another add-on. | Check extensions.blender.org and GitHub before publishing. |

### How it would feel to use
```
3D Viewport → N sidebar → "Animation Lab" tab
┌──────────────────────────────────────────┐
│ Skeleton: [Human ▾]  Search: [walk      ]│
│ Category: [All ▾]                        │
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐              │
│ │ 🧍 │ │ 🏃 │ │ 🧍 │ │ 🥊 │   ← thumbnails  │
│ │Walk│ │Jog │ │Idle│ │Jab │              │
│ └────┘ └────┘ └────┘ └────┘              │
│ ▶ Preview   ⬇ Import skeleton            │
│ ✔ Apply to selected armature             │
│ ☐ Push to NLA     ☐ Mirror               │
│ Target: (•) Mesh2Motion rig ( ) Mixamo   │
└──────────────────────────────────────────┘
```

---

## B. How much of the project is ready

Each part is weighted by how much of the total work it is.

| # | Part of Animation Lab | Share of work | Ready now | What exists |
|---|---|---|---|---|
| 1 | Animation content | 10 % | **80 %** | 251 clips in 11 GLB files (18.4 MB) across 9 skeletons: human base 87, addon 75, mocap 16; fox 14, horse 14, kaiju 10, spider 10, snake 8, shark 7, bird 5, dragon 5. All CC0. Needs splitting into a per-clip catalog. |
| 2 | Skeletons / rigs | 5 % | **90 %** | 9 rig GLBs in `static/rigs` plus Blender sources in `mesh2motion-assets/rigs` |
| 3 | Preview thumbnails | 10 % | **50 %** | 502 MP4 previews (human 356 = dark/light). Need still images (PNG) for the Blender grid. |
| 4 | Mixamo-compatible conversion | 15 % | **60 %** | Proven in TypeScript (I2–I4, exact on Y Bot). For "apply to the user's own Mixamo armature" it must run **inside Blender**, so it needs a **Python port** (~300 lines; the maths is written down in `MixamoAnimationConverter.ts`). |
| 5 | Build pipeline (web library → add-on library) | 15 % | **20 %** | The Node + Blender-headless scripts from the Mixamo investigation prove every step: load GLB clips, convert, export, verify in Blender. Not yet a real pipeline. |
| 6 | Add-on packaging, manifest, build, tests | 5 % | **40 %** | `mocopi_m2m_retarget` gives a working template |
| 7 | Library UI (grid, search, filters, previews) | 20 % | **0 %** | n/a |
| 8 | Operators (import skeleton, apply, preview, NLA, mirror) | 15 % | **10 %** | Bone maps and the action/NLA knowledge from the Mixamo work |
| 9 | Distribution and updates | 5 % | **0 %** | n/a |
| | **Total** | 100 % | **≈ 37 %** | |

**In plain words:** the *content* and the *hard problems* are mostly solved. What's missing is the *Blender-side product*: UI, operators, packaging and the pipeline that feeds it.

---

## C. Technology to add, and how it connects

### New
| Technology | Used for |
|---|---|
| **Python 3.11** (bundled with Blender 4.2+) | All add-on code |
| **Blender Python API (`bpy`, `mathutils`)** | Panels, operators, importing actions and rigs, NLA strips, the Mixamo conversion maths (`mathutils.Quaternion`/`Matrix` replace three.js) |
| **Blender Extensions format** (`blender_manifest.toml`, Blender 4.2+) | Packaging, install from disk, listing on extensions.blender.org |
| **`bpy.utils.previews`** | Loading thumbnail images into the grid |
| **`.blend` asset libraries** (one per skeleton, built in advance) | Shipping rigs and actions in Blender's native format. Appending from a `.blend` is instant and needs no conversion in the user's Blender. |
| **Blender in headless mode** (`blender -b --python …`) | Build step: turns GLB clips into `.blend` libraries and renders thumbnails. Also runs the add-on's tests. |
| **GitHub Actions** | Automatic tests and building the add-on zip on every push |
| **GitHub Releases** | Hosting the add-on zip for download |

### Reused from this project
| Existing piece | Role in Animation Lab |
|---|---|
| `static/animations/*.glb`, `static/rigs/*.glb` | Source of all content |
| `RigConfig.ts` (skeleton list, animation files) | Source of the catalog (names, skeleton types) |
| `MixamoBoneOrientationRules.ts`, `MixamoAnimationConverter.ts` | The rule and maths to port to Python for "apply to Mixamo armature" |
| `MixamoMapper.ts` | Mesh2Motion ↔ Mixamo bone names (to copy into a JSON bone map) |
| Node/esbuild scripts (investigation) | Starting point for the build pipeline |
| `mocopi_m2m_retarget` add-on | Structure: manifest, `build.py`, panel, tests |

### How the pieces connect
```
mesh2motion-app/static/animations/*.glb ─┐
mesh2motion-app/static/rigs/*.glb ───────┤
                                         ▼
          BUILD PIPELINE (runs on your computer or in GitHub Actions)
          ├─ Blender headless: import GLBs → one .blend per skeleton
          │     (rig + every clip as an action, marked as assets)
          ├─ Blender headless: render one thumbnail PNG per clip
          └─ write catalog.json (name, skeleton, category, duration, thumbnail)
                                         ▼
          animation_lab/  (the add-on)
          ├─ blender_manifest.toml
          ├─ __init__.py, ui.py, operators.py, mixamo.py, preview.py
          └─ library/  human.blend, fox.blend, …, thumbnails/, catalog.json
                                         ▼
          animation_lab-x.y.z.zip  →  GitHub Releases / extensions.blender.org
                                         ▼
          User's Blender: N panel → browse → preview → import rig → apply / push to NLA
```

**Size check:** the whole library is about 18 MB of GLB today. As `.blend` files plus thumbnails, it should still be tens of MB, small enough to **ship inside the add-on**. That means it works offline, and no server is needed.

---

## D. Can it be built for free?

**Yes.**

| Need | Free option | Notes |
|---|---|---|
| Blender, Python | Free and open source | n/a |
| Code hosting | GitHub (public repo) | Already in use: `abdimanan/the-mesh2motion` |
| Automated tests and builds | GitHub Actions | Free for public repos |
| Downloads | GitHub Releases | Free |
| Store listing | extensions.blender.org | Free. Add-on code must be **GPL-3.0-or-later** (Blender's rule for add-ons; the Mesh2Motion code is MIT, which is compatible). Assets can stay CC0. Has a review process and a size limit; check the current rules before submitting. |
| Optional online catalog (if the library later outgrows the zip) | GitHub Pages, jsDelivr, or Cloudflare Pages (the app already has a Cloudflare config) | The add-on must declare network access in its manifest and respect Blender's *Allow Online Access* setting. |

**What would cost money** (and isn't needed): user accounts, uploads from users, ratings, a database, or paid assets. That's what makes BlenderKit a big product with servers. Animation Lab can do without all of it.

---

## E. How big is it compared to the Mixamo feature?

### What the Mixamo feature took
| | Mixamo feature |
|---|---|
| Phases | 5 investigation + 4 implementation |
| App code added | ~1,200 lines of TypeScript |
| Tests added | ~1,000 lines (39 tests) |
| Docs | ~1,600 lines |
| New UI | 1 preset button + 2 notes in an existing popup |

### Animation Lab estimate
| Part | Rough size |
|---|---|
| Build pipeline (Node + Blender headless) | 500–800 lines |
| Add-on: UI (grid, search, filters, previews) | 600–1,000 lines Python |
| Add-on: operators (import, apply, preview, NLA, mirror) | 500–800 lines Python |
| Add-on: Mixamo conversion in Python | 300–500 lines |
| Packaging, preferences, catalog loading | 200–400 lines |
| Tests (Blender headless) | 800–1,200 lines |
| **Total code** | **~3,000–4,700 lines** |

| Version | Compared to the Mixamo feature |
|---|---|
| **MVP**: Human only, Mesh2Motion rig, still thumbnails, browse + import skeleton + apply + push to NLA | **≈ 1.5×** |
| **Full**: all 9 skeletons, viewport preview, Mixamo mode, mirror, extensions.blender.org release | **≈ 3–4×** |

It's bigger mainly because it's a **new product with its own UI**, while the Mixamo feature extended an existing export.

---

## Proposed phases (for when we start)

| Phase | Work | MVP? |
|---|---|---|
| **AL1** Catalog + build pipeline | GLBs → `.blend` per skeleton (rig + actions) + `catalog.json` | ✅ |
| **AL2** Thumbnails | Render one still per clip in Blender headless | ✅ (human only) |
| **AL3** Add-on skeleton | Manifest, panel, preferences, `build.py` (from the mocopi template) | ✅ |
| **AL4** Library browser UI | Grid, search, skeleton and category filters | ✅ |
| **AL5** Import + apply | Import rig, apply action to the selected armature, push to NLA, mirror | ✅ |
| **AL6** Viewport preview | Play the clip on a temporary preview armature | |
| **AL7** Mixamo mode | Python port of the converter; target = the user's selected Mixamo armature (no Mixamo data shipped) | |
| **AL8** Tests, CI, release | Blender headless tests, GitHub Actions, GitHub Release, extensions.blender.org submission | partly |

Each phase would get its own report in `docs/animation-lab/`, the same way as the Mixamo work.

## Decisions to make before starting
1. **MVP scope:** Human only first, or all 9 skeletons from the start?
2. **Where the add-on lives:** a new folder in `the-mesh2motion` (e.g. `animation-lab/`), or its own GitHub repo?
3. **Distribution:** GitHub Releases only, or also extensions.blender.org (requires GPL-3.0-or-later for the add-on code)?
4. **Name check:** confirm "Animation Lab" is free to use.
