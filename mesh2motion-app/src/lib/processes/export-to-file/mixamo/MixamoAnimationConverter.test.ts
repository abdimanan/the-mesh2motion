import { describe, it, expect } from 'vitest'
import { type AnimationClip, AnimationMixer, type Bone, Quaternion, Vector3 } from 'three'
import { MixamoRigBuilder, type MixamoRig } from './MixamoRigBuilder'
import { MixamoAnimationConverter } from './MixamoAnimationConverter'
import { MIXAMO_STANDARD_SKELETON } from './MixamoStandardSkeleton'
import { load_mesh2motion_test_human, make_test_clip, type Mesh2MotionTestHuman } from './mixamo-test-helpers'

// a looping mixer wraps the clip's end time back to frame 0, so stay inside the clip
const SAMPLE_TIMES = [0.25, 0.5, 0.9]

// keyframe values are stored as float32, which adds up to a tenth of a degree down a finger
const MAX_ROTATION_ERROR_DEGREES = 0.25

/** The Mesh2Motion skeleton playing the original clip at a time. */
function pose_source (human: Mesh2MotionTestHuman, clip: AnimationClip, time: number): AnimationMixer {
  const mixer = new AnimationMixer(human.scene)
  mixer.clipAction(clip).play()
  mixer.setTime(time)
  human.scene.updateMatrixWorld(true)
  return mixer
}

/** The Mixamo rig playing the converted clip at a time. */
function pose_target (rig: MixamoRig, converted: ReturnType<typeof MixamoAnimationConverter.convert_clip>, time: number): void {
  const mixer = new AnimationMixer(rig.root_bone)
  mixer.clipAction(converted).play()
  mixer.setTime(time)
  rig.root_bone.updateMatrixWorld(true)
}

function world_position (bone: Bone): Vector3 {
  return new Vector3().setFromMatrixPosition(bone.matrixWorld)
}

function world_rotation (bone: Bone): Quaternion {
  return new Quaternion().setFromRotationMatrix(bone.matrixWorld)
}

describe('MixamoAnimationConverter.convert_clip', () => {
  it('moves every joint of a rig with the same proportions exactly like the Mesh2Motion skeleton', async () => {
    const human = await load_mesh2motion_test_human()
    const clip = make_test_clip(human.bones) // keys are built from the rest pose
    const rig = MixamoRigBuilder.build_from_mesh2motion([human.skinned_mesh])
    const converted = MixamoAnimationConverter.convert_clip([human.skinned_mesh], clip, rig)

    SAMPLE_TIMES.forEach((time) => {
      pose_source(human, clip, time)
      pose_target(rig, converted, time)

      rig.source_bone_names.forEach((source_name, target_name) => {
        const source_bone = human.bones.find(bone => bone.name === source_name) as Bone
        const expected = world_position(source_bone).multiplyScalar(100)
        const actual = world_position(rig.bones.get(target_name) as Bone)
        expect(actual.distanceTo(expected), `${target_name} at ${time}s`).toBeLessThan(0.05)
      })
    })
  })

  it('gives each bone of a different skeleton the same world rotation change as its Mesh2Motion bone', async () => {
    const human = await load_mesh2motion_test_human()
    const clip = make_test_clip(human.bones) // keys are built from the rest pose
    const rig = MixamoRigBuilder.build_from_joint_positions(
      new Map(Object.entries(MIXAMO_STANDARD_SKELETON).map(([name, joint]) => [name, new Vector3(...joint.position)])))
    const source_rig = MixamoRigBuilder.build_from_mesh2motion([human.skinned_mesh])
    const converted = MixamoAnimationConverter.convert_clip([human.skinned_mesh], clip, rig)

    const source_rest = new Map(human.bones.map(bone => [bone.name, world_rotation(bone)]))
    const target_rest = new Map([...rig.bones].map(([name, bone]) => [name, world_rotation(bone)]))

    SAMPLE_TIMES.forEach((time) => {
      pose_source(human, clip, time)
      pose_target(rig, converted, time)

      rig.bones.forEach((bone, target_name) => {
        if (bone.children.length === 0) return // end bones are not keyed, like in Mixamo clips
        const source_bone = human.bones.find(candidate => candidate.name === source_rig.source_bone_names.get(target_name)) as Bone

        const source_change = world_rotation(source_bone).multiply((source_rest.get(source_bone.name) as Quaternion).clone().invert())
        const target_change = world_rotation(bone).multiply((target_rest.get(target_name) as Quaternion).clone().invert())
        expect(source_change.angleTo(target_change) * 180 / Math.PI, `${target_name} at ${time}s`).toBeLessThan(MAX_ROTATION_ERROR_DEGREES)
      })
    })
  })

  it('scales root motion by the hip height so a taller character covers more ground', async () => {
    const human = await load_mesh2motion_test_human()
    const clip = make_test_clip(human.bones) // keys are built from the rest pose
    const rig = MixamoRigBuilder.build_from_joint_positions(
      new Map(Object.entries(MIXAMO_STANDARD_SKELETON).map(([name, joint]) => [name, new Vector3(...joint.position)])))
    const converted = MixamoAnimationConverter.convert_clip([human.skinned_mesh], clip, rig)

    const pelvis = human.bones.find(bone => bone.name === 'pelvis') as Bone
    const source_start = world_position(pelvis)
    const target_start = world_position(rig.root_bone)
    const hip_height_ratio = target_start.y / (source_start.y * 100)

    pose_source(human, clip, 0.9)
    pose_target(rig, converted, 0.9)

    const source_travel = world_position(pelvis).sub(source_start).multiplyScalar(100)
    const target_travel = world_position(rig.root_bone).sub(target_start)
    expect(target_travel.distanceTo(source_travel.multiplyScalar(hip_height_ratio))).toBeLessThan(0.01)
    expect(target_travel.length()).toBeGreaterThan(30) // the root has moved 0.36 m by then
  })

  it('keys every bone but the end bones, binds tracks by uuid, and samples at 30 fps', async () => {
    const human = await load_mesh2motion_test_human()
    const clip = make_test_clip(human.bones) // keys are built from the rest pose
    const rig = MixamoRigBuilder.build_from_mesh2motion([human.skinned_mesh])
    const converted = MixamoAnimationConverter.convert_clip([human.skinned_mesh], clip, rig)

    const quaternion_tracks = converted.tracks.filter(track => track.name.endsWith('.quaternion'))
    const position_tracks = converted.tracks.filter(track => track.name.endsWith('.position'))

    expect(quaternion_tracks).toHaveLength(52)
    expect(position_tracks.map(track => track.name)).toEqual([`${rig.root_bone.uuid}.position`])
    expect(converted.tracks.every(track => !track.name.includes('mixamorig'))).toBe(true)
    expect(converted.name).toBe('Test_Move')
    expect(converted.duration).toBe(1)
    expect(Array.from(converted.tracks[0].times)).toHaveLength(31)
  })
})
