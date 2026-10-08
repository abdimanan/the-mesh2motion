import {
  AnimationClip, type Bone, type Interpolant, type KeyframeTrack, Matrix4, PropertyBinding, Quaternion,
  QuaternionKeyframeTrack, type SkinnedMesh, Vector3, VectorKeyframeTrack
} from 'three'
import { MixamoMapper } from '../../../../retarget/bone-automap/MixamoMapper.ts'
import { ExportRestPoseService } from '../ExportRestPoseService.ts'
import { METERS_TO_CENTIMETERS, type MixamoRig } from './MixamoRigBuilder.ts'

export interface MixamoConversionOptions {
  /** frames per second the converted clips are sampled at */
  fps?: number
  /** multiplier from the Mesh2Motion scene units to the rig's units (meters -> centimeters) */
  scale?: number
}

const DEFAULT_FPS = 30
const MAPPER_PREFIX = 'mixamorig'

// createInterpolant() is assigned at runtime by setInterpolation() and picks the right
// interpolant for the track's mode (linear, discrete, glTF cubic). The type definitions
// leave it out.
type TrackWithInterpolant = KeyframeTrack & { createInterpolant: () => Interpolant }

interface SourceBone {
  bone: Bone
  rest_local: Matrix4
  parent: SourceBone | null
  /** world matrix of the non-bone parent above a root bone (the mesh or armature) */
  root_parent_world: Matrix4 | null
  rest_world: Matrix4
  quaternion_track: Interpolant | null
  position_track: Interpolant | null
  scale_track: Interpolant | null
}

/**
 * Re-expresses Mesh2Motion animation clips on a Mixamo-convention skeleton.
 *
 * Blender plays keyframes relative to each bone's own rest axes, and the Mixamo bones have
 * different axes from the Mesh2Motion ones (see MixamoBoneOrientationRules). Renaming the
 * tracks is therefore not enough: every keyframe is converted so each Mixamo bone ends up
 * with the same world rotation change as the Mesh2Motion bone it was built from.
 *
 * For each sampled time t, with O the constant offset between the two rest poses:
 *   W_mixamo(bone, t) = W_m2m(source, t) * O,   O = W_m2m_rest(source)^-1 * W_mixamo_rest(bone)
 *   local(bone, t)    = W_mixamo(parent, t)^-1 * W_mixamo(bone, t)
 * Hips also carries the root motion, scaled by the ratio of the two hip heights so the
 * feet stay on the ground on a taller or shorter Mixamo character.
 *
 * Tracks are bound by bone uuid ("<uuid>.quaternion"). Mixamo names contain a colon, which
 * three.js track names cannot hold, and the FBX exporter resolves tracks by uuid as well.
 */
export class MixamoAnimationConverter {
  /**
   * @param source_skinned_meshes the Mesh2Motion human the clips were made for
   * @param clips Mesh2Motion clips (tracks named "<mesh2motion bone>.<property>")
   * @param target_rig skeleton to convert onto. Its source_bone_names say which Mesh2Motion
   *   bone drives each Mixamo bone; when empty the standard Mixamo mapping is used
   */
  public static convert_clips (
    source_skinned_meshes: SkinnedMesh[],
    clips: AnimationClip[],
    target_rig: MixamoRig,
    options: MixamoConversionOptions = {}
  ): AnimationClip[] {
    return clips.map(clip => this.convert_clip(source_skinned_meshes, clip, target_rig, options))
  }

  public static convert_clip (
    source_skinned_meshes: SkinnedMesh[],
    clip: AnimationClip,
    target_rig: MixamoRig,
    options: MixamoConversionOptions = {}
  ): AnimationClip {
    const fps = options.fps ?? DEFAULT_FPS
    const scale = options.scale ?? METERS_TO_CENTIMETERS

    const source_bones = this.prepare_source_bones(source_skinned_meshes, clip)
    const source_for_target = this.source_bones_for_target(target_rig, source_bones)

    // constant per-bone offset between the Mesh2Motion and Mixamo rest rotations
    const rest_offsets = new Map<string, Quaternion>()
    source_for_target.forEach((source, target_name) => {
      const source_rest_rotation = new Quaternion().setFromRotationMatrix(source.rest_world)
      rest_offsets.set(target_name, source_rest_rotation.invert().multiply(target_rig.rest_world_rotations.get(target_name) as Quaternion))
    })

    const hips_source = source_for_target.get('Hips') as SourceBone
    const hips_rest_source = new Vector3().setFromMatrixPosition(hips_source.rest_world).multiplyScalar(scale)
    const hips_rest_target = new Vector3().setFromMatrixPosition(target_rig.root_bone.matrixWorld)
    const hip_height_ratio = Math.abs(hips_rest_source.y) > 1e-6 ? hips_rest_target.y / hips_rest_source.y : 1

    // Mixamo keys every bone except the end bones (finger tips, HeadTop_End, Toe_End)
    const animated_targets = [...source_for_target.keys()].filter(name => (target_rig.bones.get(name) as Bone).children.length > 0)

    const frame_count = Math.max(1, Math.round(clip.duration * fps))
    const times: number[] = []
    for (let frame = 0; frame <= frame_count; frame++) times.push(Math.min(frame / fps, clip.duration))

    const rotation_values = new Map<string, number[]>(animated_targets.map(name => [name, []]))
    const hips_positions: number[] = []

    const target_world_rotations = new Map<string, Quaternion>()
    const parent_world_rotation = new Quaternion()
    const local_rotation = new Quaternion()

    times.forEach((time) => {
      const source_world = this.sample_source_world(source_bones, time)

      target_world_rotations.clear()
      source_for_target.forEach((source, target_name) => {
        const world_rotation = new Quaternion().setFromRotationMatrix(source_world.get(source) as Matrix4)
        target_world_rotations.set(target_name, world_rotation.multiply(rest_offsets.get(target_name) as Quaternion))
      })

      animated_targets.forEach((target_name) => {
        const bone = target_rig.bones.get(target_name) as Bone
        const parent_name = this.target_parent_name(target_rig, bone)
        const world_rotation = target_world_rotations.get(target_name) as Quaternion

        if (parent_name === null) {
          local_rotation.copy(world_rotation)
        } else {
          parent_world_rotation.copy(target_world_rotations.get(parent_name) ?? this.rest_world_rotation(target_rig, parent_name))
          local_rotation.copy(parent_world_rotation.invert()).multiply(world_rotation)
        }

        const values = rotation_values.get(target_name) as number[]
        this.push_continuous_quaternion(values, local_rotation)
      })

      const hips_now = new Vector3().setFromMatrixPosition(source_world.get(hips_source) as Matrix4).multiplyScalar(scale)
      const hips_target = hips_now.sub(hips_rest_source).multiplyScalar(hip_height_ratio).add(hips_rest_target)
      hips_positions.push(hips_target.x, hips_target.y, hips_target.z)
    })

    const tracks: KeyframeTrack[] = animated_targets.map((target_name) => {
      const bone = target_rig.bones.get(target_name) as Bone
      return new QuaternionKeyframeTrack(`${bone.uuid}.quaternion`, times, rotation_values.get(target_name) as number[])
    })
    tracks.push(new VectorKeyframeTrack(`${target_rig.root_bone.uuid}.position`, times, hips_positions))

    return new AnimationClip(clip.name, clip.duration, tracks)
  }

  /** Mesh2Motion bones at their bind pose, with the clip's tracks ready to sample. */
  private static prepare_source_bones (source_skinned_meshes: SkinnedMesh[], clip: AnimationClip): Map<string, SourceBone> {
    const bind_world_by_bone = ExportRestPoseService.bind_world_matrices(source_skinned_meshes)
    const by_bone = new Map<Bone, SourceBone>()
    const by_name = new Map<string, SourceBone>()

    bind_world_by_bone.forEach((rest_world, bone) => {
      const source: SourceBone = {
        bone,
        rest_local: new Matrix4(),
        parent: null,
        root_parent_world: null,
        rest_world,
        quaternion_track: null,
        position_track: null,
        scale_track: null
      }
      by_bone.set(bone, source)
      by_name.set(bone.name, source)
    })

    by_bone.forEach((source, bone) => {
      const parent = bone.parent !== null ? by_bone.get(bone.parent as Bone) ?? null : null
      source.parent = parent

      let parent_world: Matrix4
      if (parent !== null) {
        parent_world = parent.rest_world
      } else {
        bone.parent?.updateWorldMatrix(true, false)
        parent_world = bone.parent !== null ? bone.parent.matrixWorld.clone() : new Matrix4()
        source.root_parent_world = parent_world
      }

      source.rest_local.copy(parent_world).invert().multiply(source.rest_world)
    })

    clip.tracks.forEach((track) => {
      const parsed = PropertyBinding.parseTrackName(track.name)
      const source = by_name.get(parsed.nodeName)
      if (source === undefined) return

      if (parsed.propertyName === 'quaternion') source.quaternion_track = (track as TrackWithInterpolant).createInterpolant()
      if (parsed.propertyName === 'position') source.position_track = (track as TrackWithInterpolant).createInterpolant()
      if (parsed.propertyName === 'scale') source.scale_track = (track as TrackWithInterpolant).createInterpolant()
    })

    return by_name
  }

  /** Forward kinematics of the Mesh2Motion skeleton at one moment of the clip. */
  private static sample_source_world (source_bones: Map<string, SourceBone>, time: number): Map<SourceBone, Matrix4> {
    const world_by_source = new Map<SourceBone, Matrix4>()
    const position = new Vector3()
    const rotation = new Quaternion()
    const bone_scale = new Vector3()

    const world_of = (source: SourceBone): Matrix4 => {
      const cached = world_by_source.get(source)
      if (cached !== undefined) return cached

      source.rest_local.decompose(position, rotation, bone_scale)
      if (source.position_track !== null) position.fromArray(source.position_track.evaluate(time) as unknown as number[])
      if (source.quaternion_track !== null) rotation.fromArray(source.quaternion_track.evaluate(time) as unknown as number[]).normalize()
      if (source.scale_track !== null) bone_scale.fromArray(source.scale_track.evaluate(time) as unknown as number[])

      const local = new Matrix4().compose(position, rotation, bone_scale)
      const parent_world = source.parent !== null ? world_of(source.parent) : source.root_parent_world as Matrix4
      const world = new Matrix4().multiplyMatrices(parent_world, local)
      world_by_source.set(source, world)
      return world
    }

    source_bones.forEach(source => world_of(source))
    return world_by_source
  }

  private static source_bones_for_target (target_rig: MixamoRig, source_bones: Map<string, SourceBone>): Map<string, SourceBone> {
    const mapping = new Map<string, SourceBone>()

    if (target_rig.source_bone_names.size > 0) {
      target_rig.source_bone_names.forEach((source_name, target_name) => {
        const source = source_bones.get(source_name)
        if (source !== undefined && target_rig.bones.has(target_name)) mapping.set(target_name, source)
      })
    } else {
      source_bones.forEach((source, source_name) => {
        const mapped = MixamoMapper.map_source_bone_name_to_mixamo(source_name)
        if (mapped === undefined) return
        const target_name = mapped.slice(MAPPER_PREFIX.length)
        if (target_rig.bones.has(target_name)) mapping.set(target_name, source)
      })
    }

    if (!mapping.has('Hips')) {
      throw new Error('The Mesh2Motion skeleton has no bone that drives Mixamo Hips (pelvis)')
    }

    return mapping
  }

  private static target_parent_name (target_rig: MixamoRig, bone: Bone): string | null {
    if (bone === target_rig.root_bone || bone.parent === null) return null
    const parent_name = bone.parent.name
    return parent_name.slice(parent_name.indexOf(':') + 1)
  }

  private static rest_world_rotation (target_rig: MixamoRig, name: string): Quaternion {
    return target_rig.rest_world_rotations.get(name) ?? new Quaternion()
  }

  /** Keeps consecutive keys in the same hemisphere so interpolation never takes the long way round. */
  private static push_continuous_quaternion (values: number[], quaternion: Quaternion): void {
    const count = values.length
    if (count >= 4) {
      const dot = values[count - 4] * quaternion.x + values[count - 3] * quaternion.y +
        values[count - 2] * quaternion.z + values[count - 1] * quaternion.w
      if (dot < 0) {
        values.push(-quaternion.x, -quaternion.y, -quaternion.z, -quaternion.w)
        return
      }
    }
    values.push(quaternion.x, quaternion.y, quaternion.z, quaternion.w)
  }
}
