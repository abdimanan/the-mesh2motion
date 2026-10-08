import { describe, it, expect } from 'vitest'
import { BoxGeometry, Bone, Float32BufferAttribute, Group, Matrix4, MeshBasicMaterial, Scene, Skeleton, SkinnedMesh, Uint16BufferAttribute } from 'three'
import { FBXExporter } from '@comfyorg/fbx-exporter-three'
import { BinaryParser } from '../../io/fbx/BinaryParser'
import { FbxBoneHierarchyService } from './FbxBoneHierarchyService'

interface TestRig {
  scene: Scene
  skinned_mesh: SkinnedMesh
  hips: Bone
  spine: Bone
}

/** How a mesh rigged in Mesh2Motion is laid out: the root bone is a child of the mesh. */
function make_mesh2motion_rig (): TestRig {
  const scene = new Scene()
  const model_root = new Group()
  model_root.name = 'Model Root'
  model_root.position.set(1, 2, 3)
  scene.add(model_root)

  const hips = new Bone()
  hips.name = 'Hips'
  hips.position.set(0, 1, 0)
  hips.rotation.set(0.3, 0, 0)
  const spine = new Bone()
  spine.name = 'Spine'
  spine.position.set(0, 0.2, 0)
  hips.add(spine)

  const geometry = new BoxGeometry(1, 1, 1)
  const vertex_count = geometry.attributes.position.count
  geometry.setAttribute('skinIndex', new Uint16BufferAttribute(new Uint16Array(vertex_count * 4), 4))
  geometry.setAttribute('skinWeight', new Float32BufferAttribute(
    Float32Array.from({ length: vertex_count * 4 }, (_, index) => (index % 4 === 0 ? 1 : 0)), 4))

  const skinned_mesh = new SkinnedMesh(geometry, new MeshBasicMaterial())
  skinned_mesh.name = 'Body'
  skinned_mesh.position.set(0, 0.5, 0)
  skinned_mesh.add(hips)
  model_root.add(skinned_mesh)
  skinned_mesh.bind(new Skeleton([hips, spine]))

  return { scene, skinned_mesh, hips, spine }
}

function world_matrix (bone: Bone): Matrix4 {
  bone.updateWorldMatrix(true, false)
  return bone.matrixWorld.clone()
}

describe('FbxBoneHierarchyService.lift_bones_out_of_meshes', () => {
  it('moves a root bone from under its mesh to beside it without moving it', () => {
    const { scene, skinned_mesh, hips } = make_mesh2motion_rig()
    const hips_world_before = world_matrix(hips)

    FbxBoneHierarchyService.lift_bones_out_of_meshes(scene)

    expect(hips.parent).toBe(skinned_mesh.parent)
    world_matrix(hips).elements.forEach((value, index) => {
      expect(value).toBeCloseTo(hips_world_before.elements[index], 6)
    })
  })

  it('puts the bone back under the mesh with its original local transform', () => {
    const { scene, skinned_mesh, hips } = make_mesh2motion_rig()
    const local_position = hips.position.clone()
    const local_quaternion = hips.quaternion.clone()

    const restore = FbxBoneHierarchyService.lift_bones_out_of_meshes(scene)
    restore()

    expect(hips.parent).toBe(skinned_mesh)
    expect(hips.position.equals(local_position)).toBe(true)
    expect(hips.quaternion.equals(local_quaternion)).toBe(true)
  })

  it('leaves bones that are already beside the mesh alone', () => {
    const { scene, skinned_mesh, hips, spine } = make_mesh2motion_rig()
    skinned_mesh.parent?.attach(hips)

    FbxBoneHierarchyService.lift_bones_out_of_meshes(scene)

    expect(hips.parent).toBe(skinned_mesh.parent)
    expect(spine.parent).toBe(hips)
  })

  it('writes an FBX where no bone hangs off the mesh model', async () => {
    const { scene } = make_mesh2motion_rig()

    const restore = FbxBoneHierarchyService.lift_bones_out_of_meshes(scene)
    const bytes = await new FBXExporter().parseAsync(scene, { preset: 'blender' })
    restore()

    const tree = new BinaryParser().parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    const models = tree.Objects.Model as Record<string, { propertyList: [number, string, string] }>
    const model_type = (id: number): string | undefined => models[String(id)]?.propertyList[2]
    const connections = tree.Connections.connections as Array<[number, number]>

    const bone_parent_types = connections
      .filter(([child_id, parent_id]) => model_type(child_id) === 'LimbNode' && models[String(parent_id)] !== undefined)
      .map(([, parent_id]) => model_type(parent_id))

    expect(bone_parent_types.length).toBeGreaterThan(0)
    expect(bone_parent_types).not.toContain('Mesh')
  })
})
