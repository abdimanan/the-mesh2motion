import { describe, it, expect } from 'vitest'
import { BoxGeometry, Bone, Float32BufferAttribute, Group, MeshBasicMaterial, Scene, Skeleton, SkinnedMesh, Uint16BufferAttribute, Vector3 } from 'three'
import { ExportRestPoseService } from './ExportRestPoseService'

interface TestRig {
  model_root: Group
  skinned_mesh: SkinnedMesh
  hips: Bone
  spine: Bone
}

/** Bound in a T-pose-like rest, with the root bone under the mesh like the Create page does. */
function make_rig (): TestRig {
  const scene = new Scene()
  const model_root = new Group()
  scene.add(model_root)

  const hips = new Bone()
  hips.name = 'Hips'
  hips.position.set(0, 1, 0)
  const spine = new Bone()
  spine.name = 'Spine'
  spine.position.set(0, 0.25, 0)
  spine.rotation.set(0, 0, 0.2)
  hips.add(spine)

  const geometry = new BoxGeometry(1, 1, 1)
  const vertex_count = geometry.attributes.position.count
  geometry.setAttribute('skinIndex', new Uint16BufferAttribute(new Uint16Array(vertex_count * 4), 4))
  geometry.setAttribute('skinWeight', new Float32BufferAttribute(
    Float32Array.from({ length: vertex_count * 4 }, (_, index) => (index % 4 === 0 ? 1 : 0)), 4))

  const skinned_mesh = new SkinnedMesh(geometry, new MeshBasicMaterial())
  skinned_mesh.add(hips)
  model_root.add(skinned_mesh)
  model_root.updateMatrixWorld(true)
  skinned_mesh.bind(new Skeleton([hips, spine]))

  return { model_root, skinned_mesh, hips, spine }
}

/**
 * The bind pose is the pose where skinning leaves the mesh exactly as it was modelled.
 * applyBoneTransform runs the same maths as the skinning shader.
 */
function expect_mesh_undeformed (skinned_mesh: SkinnedMesh): void {
  skinned_mesh.updateMatrixWorld(true)
  const positions = skinned_mesh.geometry.attributes.position
  const vertex = new Vector3()

  for (let index = 0; index < positions.count; index++) {
    vertex.fromBufferAttribute(positions, index)
    const original = vertex.clone()
    skinned_mesh.applyBoneTransform(index, vertex)
    expect(vertex.distanceTo(original)).toBeLessThan(1e-5)
  }
}

/** Simulates the preview being mid-animation when Download is clicked. */
function play_some_frame (rig: TestRig): void {
  rig.hips.position.set(0.3, 0.8, -0.1)
  rig.hips.rotation.set(0.5, 0.2, 0)
  rig.spine.rotation.set(-0.4, 0, 0.9)
  rig.hips.updateMatrixWorld(true)
}

describe('ExportRestPoseService.apply_bind_pose', () => {
  it('poses an animated skeleton back at its bind pose', () => {
    const rig = make_rig()
    play_some_frame(rig)

    ExportRestPoseService.apply_bind_pose([rig.skinned_mesh])

    expect_mesh_undeformed(rig.skinned_mesh)
    expect(rig.spine.rotation.z).toBeCloseTo(0.2, 5)
  })

  it('stays correct when the model was scaled after it was bound', () => {
    // the retarget page scales large imports down after loading them
    const rig = make_rig()
    rig.model_root.scale.setScalar(0.01)
    rig.model_root.updateMatrixWorld(true)
    play_some_frame(rig)

    ExportRestPoseService.apply_bind_pose([rig.skinned_mesh])

    expect_mesh_undeformed(rig.skinned_mesh)

    // the bone locals must not pick up the scale a second time
    expect(rig.hips.position.distanceTo(new Vector3(0, 1, 0))).toBeLessThan(1e-5)
    expect(rig.hips.scale.distanceTo(new Vector3(1, 1, 1))).toBeLessThan(1e-5)
    expect(rig.spine.position.distanceTo(new Vector3(0, 0.25, 0))).toBeLessThan(1e-5)
  })

  it('restores the pose the bones were in before', () => {
    const rig = make_rig()
    play_some_frame(rig)
    const hips_position = rig.hips.position.clone()
    const spine_quaternion = rig.spine.quaternion.clone()

    const restore = ExportRestPoseService.apply_bind_pose([rig.skinned_mesh])
    restore()

    expect(rig.hips.position.equals(hips_position)).toBe(true)
    expect(rig.spine.quaternion.equals(spine_quaternion)).toBe(true)
  })
})
