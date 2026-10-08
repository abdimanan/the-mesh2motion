# the-mesh2motion

My working copy of [Mesh2Motion](https://mesh2motion.org/): the web app and its Blender source assets, with an added **Mixamo-compatible FBX download for Blender**.

| Folder | What it is | Based on |
|---|---|---|
| `mesh2motion-app/` | The Mesh2Motion web app (TypeScript, three.js, Vite) | [Mesh2Motion/mesh2motion-app](https://github.com/Mesh2Motion/mesh2motion-app) |
| `mesh2motion-assets/` | Blender source files for the rigs, models and animations | [Mesh2Motion/mesh2motion-assets](https://github.com/Mesh2Motion/mesh2motion-assets) |

## What I added

In the app's download options, **FBX 7.4 + FBX Preset `blender` + Bone Naming `Mixamo`** downloads the standard Mixamo skeleton (Y Bot) with the selected animations converted onto it. In Blender the actions play on a Mixamo armature as is, so they can be mixed with Mixamo clips in the NLA Editor.

It also fixes FBX downloads that showed only empties or no armature in Blender, came in 100× too small or turned around, or had a random animation frame as their rest pose.

The full investigation and implementation notes are in [`mesh2motion-app/docs/download animation as mixamo bone rig/`](mesh2motion-app/docs/download%20animation%20as%20mixamo%20bone%20rig/), and the commands to run the app are in [`mesh2motion-app/docs/COMMANDS.md`](mesh2motion-app/docs/COMMANDS.md).

## Run the app

```bash
cd mesh2motion-app
npm install
npm run dev        # http://localhost:5173
npm test           # unit tests
```

## Licenses

Mesh2Motion's code is MIT licensed and its art assets are CC0. See `mesh2motion-app/LICENSE-MIT.MD` and `mesh2motion-app/LICENSE-CC0.MD`. Mixamo downloads used for testing are not included in this repository.
