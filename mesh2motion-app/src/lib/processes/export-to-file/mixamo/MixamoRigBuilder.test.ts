import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { type Bone, BoxGeometry, Float32BufferAttribute, MeshBasicMaterial, type Object3D, Quaternion, Skeleton, SkinnedMesh, Uint16BufferAttribute, Vector3 } from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { MixamoRigBuilder, type MixamoRig } from './MixamoRigBuilder'
import { MIXAMO_BONE_RULES } from './MixamoBoneOrientationRules'
import { MIXAMO_STANDARD_SKELETON } from './MixamoStandardSkeleton'

/** End bones (no children) are never animated by Mixamo, so their axes do not affect any clip. */
const PARENT_BONES = new Set(MIXAMO_BONE_RULES.map(rule => rule.parent))
const END_BONES = new Set(MIXAMO_BONE_RULES.filter(rule => !PARENT_BONES.has(rule.name)).map(rule => rule.name))

const MAX_AXIS_ERROR_DEGREES = 2

async function load_mesh2motion_human_rig (): Promise<Object3D> {
  const buffer = readFileSync('static/rigs/rig-human.glb')

  // allocate inside this realm. A Node ArrayBuffer fails GLTFLoader's
  // `data instanceof ArrayBuffer` check under jsdom and gets parsed as JSON instead
  const array_buffer = new ArrayBuffer(buffer.byteLength)
  new Uint8Array(array_buffer).set(buffer)

  return await new Promise((resolve, reject) => {
    new GLTFLoader().parse(array_buffer, '', (gltf) => resolve(gltf.scene), reject)
  })
}

function collect_bones (root: Object3D): Bone[] {
  const bones: Bone[] = []
  root.traverse((child) => { if ((child as Bone).isBone === true) bones.push(child as Bone) })
  return bones
}

function world_positions (bones: Bone[]): Map<Bone, Vector3> {
  const positions = new Map<Bone, Vector3>()
  bones.forEach((bone) => {
    bone.updateWorldMatrix(true, false)
    positions.set(bone, new Vector3().setFromMatrixPosition(bone.matrixWorld))
  })
  return positions
}

function reference_positions (): Map<string, Vector3> {
  return new Map(Object.entries(MIXAMO_STANDARD_SKELETON).map(([name, joint]) => [name, new Vector3(...joint.position)]))
}

function world_axis (rig: MixamoRig, bone_name: string, axis: Vector3): Vector3 {
  return axis.clone().applyQuaternion(rig.rest_world_rotations.get(bone_name) as Quaternion)
}

function angle_degrees (a: Quaternion, b: Quaternion): number {
  return a.angleTo(b) * 180 / Math.PI
}

describe('MixamoRigBuilder.build_from_joint_positions', () => {
  it('reproduces the axes of every animated Mixamo bone from its joint positions', () => {
    const rig = MixamoRigBuilder.build_from_joint_positions(reference_positions())

    const errors = Object.entries(MIXAMO_STANDARD_SKELETON)
      .filter(([name]) => !END_BONES.has(name))
      .map(([name, joint]) => ({
        name,
        degrees: angle_degrees(rig.rest_world_rotations.get(name) as Quaternion, new Quaternion(...joint.rotation))
      }))

    expect(errors).toHaveLength(52)
    errors.forEach(({ name, degrees }) => {
      expect(degrees, name).toBeLessThan(MAX_AXIS_ERROR_DEGREES)
    })
  })

  it('places every joint exactly where it was given', () => {
    const positions = reference_positions()
    const rig = MixamoRigBuilder.build_from_joint_positions(positions)

    rig.bones.forEach((bone, name) => {
      const world = new Vector3().setFromMatrixPosition(bone.matrixWorld)
      expect(world.distanceTo(positions.get(name) as Vector3), name).toBeLessThan(1e-3)
    })
  })

  it('builds the Mixamo hierarchy with Hips as the only root', () => {
    const rig = MixamoRigBuilder.build_from_joint_positions(reference_positions())

    expect(rig.bones.size).toBe(65)
    expect(rig.root_bone.name).toBe('mixamorig:Hips')
    expect(rig.root_bone.parent).toBeNull()

    MIXAMO_BONE_RULES.forEach((rule) => {
      const bone = rig.bones.get(rule.name) as Bone
      expect(bone.name).toBe(`mixamorig:${rule.name}`)
      expect(bone.parent?.name ?? null).toBe(rule.parent === null ? null : `mixamorig:${rule.parent}`)
    })
  })

  it('leaves out fingers that were removed and still orients the hand', () => {
    const positions = reference_positions()
    // ThumbAndIndex hands keep only those two fingers
    for (const name of positions.keys()) {
      if (/Hand(Middle|Ring|Pinky)\d/.test(name)) positions.delete(name)
    }

    const rig = MixamoRigBuilder.build_from_joint_positions(positions)

    expect(rig.bones.has('LeftHandMiddle1')).toBe(false)
    expect(rig.bones.has('LeftHandIndex1')).toBe(true)
    // the hand now points down the index finger instead
    const hand_y = world_axis(rig, 'LeftHand', new Vector3(0, 1, 0))
    const to_index = (positions.get('LeftHandIndex1') as Vector3).clone().sub(positions.get('LeftHand') as Vector3).normalize()
    expect(hand_y.angleTo(to_index)).toBeLessThan(1e-4)
  })

  it('refuses to build a skeleton without the core body bones', () => {
    const positions = reference_positions()
    positions.delete('LeftForeArm')

    expect(() => MixamoRigBuilder.build_from_joint_positions(positions)).toThrow(/LeftForeArm/)
  })
})

describe('MixamoRigBuilder.build_standard_mixamo', () => {
  it('builds the standard Mixamo skeleton exactly as stored', () => {
    const rig = MixamoRigBuilder.build_standard_mixamo()

    expect(rig.bones.size).toBe(65)
    expect(rig.root_bone.name).toBe('mixamorig:Hips')
    expect(rig.root_bone.position.y).toBeCloseTo(99.79, 2)
    Object.entries(MIXAMO_STANDARD_SKELETON).forEach(([name, joint]) => {
      const bone = rig.bones.get(name) as Bone
      expect(new Vector3().setFromMatrixPosition(bone.matrixWorld).distanceTo(new Vector3(...joint.position)), name).toBeLessThan(1e-3)
      expect(angle_degrees(rig.rest_world_rotations.get(name) as Quaternion, new Quaternion(...joint.rotation).normalize()), name).toBeLessThan(1e-3)
    })
  })

  it('returns fresh bones every time so exports never share a skeleton', () => {
    expect(MixamoRigBuilder.build_standard_mixamo().root_bone).not.toBe(MixamoRigBuilder.build_standard_mixamo().root_bone)
  })
})

describe('MixamoRigBuilder.build_from_mixamo_skeleton', () => {
  it('adopts a loaded Mixamo skeleton as it is, whatever the loader did to the names', () => {
    const original = MixamoRigBuilder.build_from_joint_positions(reference_positions())
    const loaded_bones = [...original.bones.values()]

    // three.js strips the colon on import, and some Mixamo files number the prefix
    loaded_bones.forEach((bone, index) => {
      bone.name = index % 2 === 0
        ? bone.name.replace('mixamorig:', 'mixamorig')
        : bone.name.replace('mixamorig:', 'mixamorig1:')
    })

    const adopted = MixamoRigBuilder.build_from_mixamo_skeleton(loaded_bones)

    expect(adopted.bones.size).toBe(65)
    expect(adopted.root_bone.name).toBe('mixamorig:Hips')
    adopted.bones.forEach((bone, name) => {
      const source = original.bones.get(name) as Bone
      expect(new Vector3().setFromMatrixPosition(bone.matrixWorld).distanceTo(new Vector3().setFromMatrixPosition(source.matrixWorld)), name).toBeLessThan(1e-3)
      expect(angle_degrees(adopted.rest_world_rotations.get(name) as Quaternion, original.rest_world_rotations.get(name) as Quaternion), name).toBeLessThan(1e-3)
    })
  })
})

describe('MixamoRigBuilder.build_from_mesh2motion_joints', () => {
  it('turns the Mesh2Motion human into a 65 bone Mixamo skeleton in centimeters', async () => {
    const scene = await load_mesh2motion_human_rig()
    const rig = MixamoRigBuilder.build_from_mesh2motion_joints(world_positions(collect_bones(scene)))

    expect(rig.bones.size).toBe(65)
    expect(rig.source_bone_names.get('Hips')).toBe('pelvis')
    expect(rig.source_bone_names.get('LeftHand')).toBe('hand_l')
    expect([...rig.bones.values()].some(bone => bone.name.includes('root'))).toBe(false)

    // Mesh2Motion pelvis sits 0.917 m up, left hand 0.75 m to the character's left
    expect(rig.root_bone.position.y).toBeCloseTo(91.7, 0)
    const left_hand = new Vector3().setFromMatrixPosition((rig.bones.get('LeftHand') as Bone).matrixWorld)
    expect(left_hand.x).toBeCloseTo(75, 0)
  })

  it('gives the Mesh2Motion bones Mixamo axes, not their own', async () => {
    const scene = await load_mesh2motion_human_rig()
    const rig = MixamoRigBuilder.build_from_mesh2motion_joints(world_positions(collect_bones(scene)))

    // Mixamo: left arm X points back (-Z), legs X points to the character's right (-X).
    // The Mesh2Motion rig has them rolled 90 and 180 degrees from that.
    expect(world_axis(rig, 'LeftArm', new Vector3(1, 0, 0)).z).toBeLessThan(-0.99)
    expect(world_axis(rig, 'RightArm', new Vector3(1, 0, 0)).z).toBeGreaterThan(0.99)
    expect(world_axis(rig, 'LeftLeg', new Vector3(1, 0, 0)).x).toBeLessThan(-0.99)
    expect(world_axis(rig, 'Hips', new Vector3(0, 1, 0)).y).toBeCloseTo(1, 6)
  })
})

describe('MixamoRigBuilder.build_from_mesh2motion', () => {
  it('uses the bind pose even while the skeleton is mid-animation', async () => {
    const scene = await load_mesh2motion_human_rig()
    const bones = collect_bones(scene)
    const rest_rig = MixamoRigBuilder.build_from_mesh2motion_joints(world_positions(bones))

    const geometry = new BoxGeometry(1, 1, 1)
    const vertex_count = geometry.attributes.position.count
    geometry.setAttribute('skinIndex', new Uint16BufferAttribute(new Uint16Array(vertex_count * 4), 4))
    geometry.setAttribute('skinWeight', new Float32BufferAttribute(
      Float32Array.from({ length: vertex_count * 4 }, (_, index) => (index % 4 === 0 ? 1 : 0)), 4))
    const skinned_mesh = new SkinnedMesh(geometry, new MeshBasicMaterial())
    scene.add(skinned_mesh)
    scene.updateMatrixWorld(true)
    skinned_mesh.bind(new Skeleton(bones))

    // play "a frame": bend the left arm and move the pelvis
    const upperarm = bones.find(bone => bone.name === 'upperarm_l') as Bone
    upperarm.rotateZ(1.2)
    const pelvis = bones.find(bone => bone.name === 'pelvis') as Bone
    pelvis.position.x += 0.3
    scene.updateMatrixWorld(true)

    const rig = MixamoRigBuilder.build_from_mesh2motion([skinned_mesh])

    rig.bones.forEach((bone, name) => {
      const expected = new Vector3().setFromMatrixPosition((rest_rig.bones.get(name) as Bone).matrixWorld)
      expect(new Vector3().setFromMatrixPosition(bone.matrixWorld).distanceTo(expected), name).toBeLessThan(1e-3)
    })
  })
})
