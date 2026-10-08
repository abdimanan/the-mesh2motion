import { type AnimationClip, Scene, type SkinnedMesh } from 'three'
import { FBXExporter } from '@comfyorg/fbx-exporter-three'
import { MixamoRigBuilder, type MixamoRig } from './MixamoRigBuilder.ts'
import { MixamoAnimationConverter } from './MixamoAnimationConverter.ts'

export interface MixamoFbxExportOptions {
  /**
   * skeleton to export onto. Defaults to the standard Mixamo skeleton (Y Bot), which is
   * what Mixamo clips use. MixamoRigBuilder.build_from_mesh2motion() keeps the user's own
   * proportions instead, at the cost of no longer lining up exactly with Mixamo clips.
   */
  target_rig?: MixamoRig
  fps?: number
}

const MIXAMO_FPS = 30

/**
 * Writes Mesh2Motion animations as an FBX laid out like a Mixamo "Without Skin" download:
 * one Armature of mixamorig: bones with Hips at the top, Mixamo bone axes, centimeters,
 * Y up and the same axis signs as Mixamo, and one take per clip. Blender imports it with
 * the same object scale (0.01) and rotation (X 90) as a Mixamo file, so the actions can be
 * mixed with Mixamo actions in the NLA Editor.
 */
export class MixamoFbxExportService {
  public static async export (
    source_skinned_meshes: SkinnedMesh[],
    clips: AnimationClip[],
    options: MixamoFbxExportOptions = {}
  ): Promise<Uint8Array> {
    const fps = options.fps ?? MIXAMO_FPS
    const rig = options.target_rig ?? MixamoRigBuilder.build_standard_mixamo()
    const converted_clips = MixamoAnimationConverter.convert_clips(source_skinned_meshes, clips, rig, { fps })

    const export_scene = new Scene()
    const original_parent = rig.root_bone.parent
    export_scene.add(rig.root_bone)

    try {
      return await new FBXExporter().parseAsync(export_scene, {
        // the data is already in centimeters, which is what UnitScaleFactor 1 declares.
        // axisForward '-Z' writes FrontAxisSign/CoordAxisSign +1, the same as Mixamo
        unitScale: 1,
        axisUp: 'Y',
        axisForward: '-Z',
        fps,
        includeAnimations: true,
        animations: converted_clips,
        onlyVisible: false,
        embedTextures: false
      })
    } finally {
      export_scene.remove(rig.root_bone)
      if (original_parent !== null) original_parent.add(rig.root_bone)
    }
  }
}
