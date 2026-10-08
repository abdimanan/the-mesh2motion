import { describe, it, expect } from 'vitest'
import { AnimationClip, BoxGeometry, Bone, Float32BufferAttribute, Group, MeshBasicMaterial, QuaternionKeyframeTrack, Skeleton, SkinnedMesh, Uint16BufferAttribute } from 'three'
import { BoneNamingStructure } from './DownloadSettings'
import { ExportBoneNamingService } from './ExportBoneNamingService'
import { ExportAnimationCleanupService } from './ExportAnimationCleanupService'

interface TestRig {
  model_root: Group
  skinned_mesh: SkinnedMesh
  pelvis: Bone
  spine: Bone
}

/** A Mesh2Motion-named rig laid out like an imported file: bones beside the mesh. */
function make_rig_with_bones_beside_mesh (): TestRig {
  const model_root = new Group()

  const pelvis = new Bone()
  pelvis.name = 'pelvis'
  const spine = new Bone()
  spine.name = 'spine_01'
  pelvis.add(spine)
  model_root.add(pelvis)

  const geometry = new BoxGeometry(1, 1, 1)
  const vertex_count = geometry.attributes.position.count
  geometry.setAttribute('skinIndex', new Uint16BufferAttribute(new Uint16Array(vertex_count * 4), 4))
  geometry.setAttribute('skinWeight', new Float32BufferAttribute(
    Float32Array.from({ length: vertex_count * 4 }, (_, index) => (index % 4 === 0 ? 1 : 0)), 4))

  const skinned_mesh = new SkinnedMesh(geometry, new MeshBasicMaterial())
  skinned_mesh.bind(new Skeleton([pelvis, spine]))
  model_root.add(skinned_mesh)

  return { model_root, skinned_mesh, pelvis, spine }
}

function make_clip (): AnimationClip {
  return new AnimationClip('Walk', 1, [
    new QuaternionKeyframeTrack('pelvis.quaternion', [0, 1], [0, 0, 0, 1, 0, 0, 0, 1]),
    new QuaternionKeyframeTrack('spine_01.quaternion', [0, 1], [0, 0, 0, 1, 0, 0, 0, 1])
  ])
}

describe('ExportBoneNamingService.apply_download_settings', () => {
  it('renames bones that sit beside the mesh instead of under it', () => {
    const rig = make_rig_with_bones_beside_mesh()

    ExportBoneNamingService.apply_download_settings([rig.skinned_mesh], [make_clip()], BoneNamingStructure.Mixamo)

    expect(rig.pelvis.name).toBe('mixamorigHips')
    expect(rig.spine.name).toBe('mixamorigSpine')
  })

  it('keeps every animation track through the export cleanup', () => {
    const rig = make_rig_with_bones_beside_mesh()
    const clip = make_clip()

    ExportBoneNamingService.apply_download_settings([rig.skinned_mesh], [clip], BoneNamingStructure.Mixamo)
    ExportAnimationCleanupService.clean_clips_for_export([clip], [rig.model_root])

    // before the fix the bones kept their old names, so cleanup dropped both tracks
    expect(clip.tracks.map(track => track.name)).toEqual(['mixamorigHips.quaternion', 'mixamorigSpine.quaternion'])
  })

  it('gives the bones their original names back', () => {
    const rig = make_rig_with_bones_beside_mesh()

    const restore = ExportBoneNamingService.apply_download_settings([rig.skinned_mesh], [make_clip()], BoneNamingStructure.Mixamo)
    restore()

    expect(rig.pelvis.name).toBe('pelvis')
    expect(rig.spine.name).toBe('spine_01')
  })
})
