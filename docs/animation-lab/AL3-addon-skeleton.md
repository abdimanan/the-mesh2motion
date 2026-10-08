# AL3: The add-on itself (installable extension + sidebar tab)

**Status:** ✅ Done
**Date:** 2026-10-08
**Previous:** [AL2-thumbnails.md](AL2-thumbnails.md)

## Goal

Turn the library into a real, installable Blender add-on: manifest, sidebar panel, preferences and packaging, following the structure of the Mesh2Motion extension already in `mesh2motion-assets` (`mocopi_m2m_retarget`).

## Result

| | |
|---|---|
| Installable file | `dist/animation_lab-0.1.0.zip` (about 45 MB, library and thumbnails included, works offline) |
| Built and validated with | **Blender's own extension tools**: `blender --command extension build` and `… validate` |
| Blender versions | 4.4 or newer (tested with 4.5 LTS). 4.4 is the minimum because the library uses the slotted-action format introduced there. |
| License | GPL-3.0-or-later (the text bundled with Blender), animations CC0 |
| Where it appears | 3D Viewport → sidebar (**N**) → **Animation Lab** tab |
| Tests | **8/8** add-on tests on the installed zip + **10/10** library tests |

### What the tab shows (AL3)
```
┌ Animation Lab ──────────────────┐
│ [Human               ▾]         │  ← skeleton (9)
│   ┌──────────┐                  │
│   │  T-pose  │                  │  ← rig thumbnail (from AL2)
│   └──────────┘                  │
│ 🎞 178 animations               │
│ 🦴 Human Rig, 66 bones          │
│ [All categories (178)  ▾]       │  ← category, with counts
│ ℹ Browsing and applying         │
│   animations arrive in the      │
│   next update.                  │
│ [⟳ Reload Library]              │
└─────────────────────────────────┘
```
If the library is missing (not built), the tab shows a clear error with the command to run, instead of breaking.

**Preferences** (*Edit → Preferences → Add-ons → Animation Lab*): thumbnail size, plus library status (number of animations and skeletons, location).

## How to install
1. `Animation-Lab-add-on/tools/package_addon.sh`
2. In Blender 4.4+: drag `dist/animation_lab-0.1.0.zip` into the window, or *Edit → Preferences → Get Extensions → ⌄ → Install from Disk…*
3. Press **N** in the 3D Viewport and choose the **Animation Lab** tab.

## Code (`Animation-Lab-add-on/animation_lab/`)

| File | Role |
|---|---|
| `blender_manifest.toml` | Extension id `animation_lab`, version 0.1.0, tags Animation/Rigging, GPL-3.0-or-later, min Blender 4.4, excludes `__pycache__` and `.blend1` |
| `__init__.py` | Registers the modules in order, unregisters in reverse |
| `library.py` | Reads `catalog.json` (cached; plain Python, no `bpy`): skeletons, animations by skeleton/category, category counts, file paths, a clear error when the library is missing or has an unknown format |
| `previews.py` | Loads thumbnails as UI icons on first use (`bpy.utils.previews`), freed on unregister |
| `properties.py` | Panel state on the **window manager** (not saved into the user's `.blend`): skeleton and category. Changing skeleton resets the category. |
| `preferences.py` | Add-on preferences: thumbnail size, library status |
| `operators.py` | `animation_lab.reload_library`: re-reads the library after a rebuild |
| `ui.py` | `ANIMLAB_PT_library`, the sidebar tab |
| `LICENSE` | GPL-3.0-or-later text |

### Tools
| File | Role |
|---|---|
| `tools/package_addon.sh` | Builds the library (unless `SKIP_LIBRARY_BUILD=1`), then the zip with `blender --command extension build`, then validates it |
| `tests/run_addon_tests.sh` | Packages, installs the zip into a **throwaway Blender user folder** (`BLENDER_USER_RESOURCES`) with `blender --command extension install-file`, then runs `test_addon.py` against the installed copy. The folder is deleted afterwards; your own Blender is never touched (checked). |

## Tests: `tests/test_addon.py` (8/8)

| Test | Checks |
|---|---|
| Installed and enabled | `bl_ext.user_default.animation_lab` is enabled, and it is the **installed copy**, not the source folder |
| Library ships inside the add-on | 251 animations, 9 skeletons, every `.blend` and every thumbnail present in the installed package |
| Registered types | sidebar panel in the "Animation Lab" tab, window-manager state, Reload works |
| Skeleton and category choices | 9 skeletons with Human first; picking a category works; changing skeleton resets it; Fox shows "All categories (14)" |
| Preferences | default thumbnail size; preferences draw and show "251 animations for 9 skeletons" |
| **Panel draws** | The panel is drawn into a **checking layout** that fails on any unknown icon, property or operator, the mistakes that otherwise only show as a broken sidebar in a real window. Also checks the rig thumbnail loads at 256×256. |
| Panel draws without a library | Shows "Animation library not found"; Reload reports it instead of failing |
| Disable and enable again | Unregisters cleanly (panel and state gone) and registers again |

## Found along the way
| Finding | What was done |
|---|---|
| The zip was 47 MB: thumbnails 14 MB, plus the previews stored in the `.blend` files | PNGs now saved at lossless maximum compression: thumbnails **14 → 9.7 MB** |
| In background mode Blender loads preview images but gives them **no icon id** (icons need a UI) | The panel simply leaves the picture out there; in a real window it shows. The test checks the image loaded at full size, and checks the icon itself only when a UI is present. |
| Drawing panels can't be tested in background mode (the template opens a real window for that) | A checking layout validates icons, properties and operators against Blender's own definitions, headless |

## Notes for later phases
- **AL4:** the browser grid goes into the same panel (`ui.py`), using `previews.icon_id()` and the thumbnail-size preference. The search text can be added to `ANIMLAB_PG_state`.
- **AL5:** operators for importing the rig and applying animations go into `operators.py`; `library.file_path(entry["blend_file"])` points at the `.blend` to append from.
- **Size:** if the zip ever needs to be smaller, the `.blend` previews could be stored at 128×128 (the PNGs stay 256).
