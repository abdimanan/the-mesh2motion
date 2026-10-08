import { Bone, Matrix4, Quaternion, type SkinnedMesh, Vector3 } from 'three'
import { MixamoMapper } from '../../../../retarget/bone-automap/MixamoMapper.ts'
import { ExportRestPoseService } from '../ExportRestPoseService.ts'
import {
  MIXAMO_BONE_RULES, MIXAMO_NAME_PREFIX, MIXAMO_REQUIRED_BONES,
  type MixamoAxisReference, type MixamoBoneRule
} from './MixamoBoneOrientationRules.ts'
import { MIXAMO_STANDARD_SKELETON } from './MixamoStandardSkeleton.ts'

/** Mixamo files are in centimeters, three.js scenes in meters. */
export const METERS_TO_CENTIMETERS = 100

// MixamoMapper names carry the prefix without a colon, because three.js strips colons
// from node names on import
const MAPPER_PREFIX = 'mixamorig'

export interface MixamoRig {
  /** mixamorig:Hips. The only root: no Mesh2Motion root bone and no Null above it */
  root_bone: Bone
  /** keyed by the Mixamo name without the prefix ('Hips', 'LeftHand', ...) */
  bones: Map<string, Bone>
  /** rest world rotation of each Mixamo bone, in the same frame as the joint positions */
  rest_world_rotations: Map<string, Quaternion>
  /** Mesh2Motion bone each Mixamo bone was built from. Empty when built from raw positions */
  source_bone_names: Map<string, string>
}

const AXIS_REFERENCES: Record<MixamoAxisReference, Vector3> = {
  '+X': new Vector3(1, 0, 0),
  '-X': new Vector3(-1, 0, 0),
  '+Z': new Vector3(0, 0, 1),
  '-Z': new Vector3(0, 0, -1)
}

const WORLD_UP = new Vector3(0, 1, 0)

/**
 * Builds a skeleton that follows Mixamo's conventions: the 65 "mixamorig:" bones, Hips at
 * the top, and every bone oriented the way Mixamo's auto-rigger would orient it (see
 * MixamoBoneOrientationRules). Joint positions come from the Mesh2Motion skeleton, so the
 * proportions are the user's own.
 */
export class MixamoRigBuilder {
  /**
   * @param skinned_meshes the Mesh2Motion human, posed however; its bind pose is used
   * @param scale multiplier from scene units to the rig's units (meters -> centimeters)
   */
  public static build_from_mesh2motion (skinned_meshes: SkinnedMesh[], scale: number = METERS_TO_CENTIMETERS): MixamoRig {
    const bind_world_by_bone = ExportRestPoseService.bind_world_matrices(skinned_meshes)
    const positions = new Map<Bone, Vector3>()
    bind_world_by_bone.forEach((matrix, bone) => positions.set(bone, new Vector3().setFromMatrixPosition(matrix)))
    return this.build_from_mesh2motion_joints(positions, scale)
  }

  /**
   * @param joint_world_positions world position of each Mesh2Motion bone at rest
   * @param scale multiplier applied to every position
   */
  public static build_from_mesh2motion_joints (joint_world_positions: Map<Bone, Vector3>, scale: number = METERS_TO_CENTIMETERS): MixamoRig {
    const positions = new Map<string, Vector3>()
    const source_bone_names = new Map<string, string>()

    joint_world_positions.forEach((position, bone) => {
      const mapped_name = MixamoMapper.map_source_bone_name_to_mixamo(bone.name)
      if (mapped_name === undefined) return // the Mesh2Motion root bone has no Mixamo equivalent

      const mixamo_name = mapped_name.slice(MAPPER_PREFIX.length)
      positions.set(mixamo_name, position.clone().multiplyScalar(scale))
      source_bone_names.set(mixamo_name, bone.name)
    })

    const rig = this.build_from_joint_positions(positions)
    rig.source_bone_names = source_bone_names
    return rig
  }

  /**
   * @param joint_positions world position of each Mixamo joint, keyed by the Mixamo name
   *   without prefix. Bones that are missing (removed fingers, tips) are left out together
   *   with everything below them.
   */
  public static build_from_joint_positions (joint_positions: Map<string, Vector3>): MixamoRig {
    return this.assemble_rig(joint_positions, (rule, position, rest_world_rotations) =>
      this.world_rotation_for(rule, position, joint_positions, rest_world_rotations))
  }

  /**
   * Adopts an existing Mixamo skeleton as it is, for example a Mixamo download loaded with
   * the FBX loader. Exporting onto the very skeleton the user's Mixamo clips were made for
   * is the only way the clips line up exactly, whatever proportions that character has.
   *
   * @param mixamo_bones the loaded bones, at their rest pose. Names may be "mixamorig:Hips",
   *   "mixamorigHips" (three.js strips the colon) or numbered like "mixamorig1:Hips"
   * @param scale multiplier from the loaded units to centimeters (1 for a Mixamo FBX)
   */
  public static build_from_mixamo_skeleton (mixamo_bones: Bone[], scale: number = 1): MixamoRig {
    const world_transforms = new Map<string, { position: Vector3, rotation: Quaternion }>()

    mixamo_bones.forEach((bone) => {
      const name = this.mixamo_short_name(bone.userData.originalName ?? bone.name)
      if (name === null || world_transforms.has(name)) return

      bone.updateWorldMatrix(true, false)
      const position = new Vector3()
      const rotation = new Quaternion()
      bone.matrixWorld.decompose(position, rotation, new Vector3())
      world_transforms.set(name, { position: position.multiplyScalar(scale), rotation })
    })

    return this.build_from_world_transforms(world_transforms)
  }

  /**
   * The standard Mixamo skeleton (Y Bot), exactly as Mixamo ships it. Mesh2Motion clips
   * converted onto it line up with Mixamo clips on the same armature.
   */
  public static build_standard_mixamo (): MixamoRig {
    return this.build_from_world_transforms(new Map(Object.entries(MIXAMO_STANDARD_SKELETON).map(([name, joint]) => [
      name,
      { position: new Vector3(...joint.position), rotation: new Quaternion(...joint.rotation).normalize() }
    ])))
  }

  /** @param world_transforms world position and rest rotation of each Mixamo bone, by short name */
  public static build_from_world_transforms (world_transforms: Map<string, { position: Vector3, rotation: Quaternion }>): MixamoRig {
    const positions = new Map([...world_transforms].map(([name, transform]) => [name, transform.position]))
    return this.assemble_rig(positions, (rule) => (world_transforms.get(rule.name) as { rotation: Quaternion }).rotation.clone())
  }

  /** 'mixamorig:LeftHand', 'mixamorigLeftHand', 'mixamorig7:LeftHand' -> 'LeftHand' */
  private static mixamo_short_name (bone_name: string): string | null {
    const short_name = bone_name.replace(/^mixamorig\d*:?/, '')
    return MIXAMO_BONE_RULES.some(rule => rule.name === short_name) ? short_name : null
  }

  private static assemble_rig (
    joint_positions: Map<string, Vector3>,
    world_rotation_of: (rule: MixamoBoneRule, position: Vector3, rest_world_rotations: Map<string, Quaternion>) => Quaternion
  ): MixamoRig {
    const missing_required = MIXAMO_REQUIRED_BONES.filter(name => !joint_positions.has(name))
    if (missing_required.length > 0) {
      throw new Error(`Cannot build a Mixamo skeleton without these bones: ${missing_required.join(', ')}`)
    }

    const bones = new Map<string, Bone>()
    const rest_world_rotations = new Map<string, Quaternion>()
    const world_matrices = new Map<string, Matrix4>()

    MIXAMO_BONE_RULES.forEach((rule) => {
      const position = joint_positions.get(rule.name)
      if (position === undefined) return
      if (rule.parent !== null && !bones.has(rule.parent)) return // the chain above it was removed

      const world_rotation = world_rotation_of(rule, position, rest_world_rotations)
      const world_matrix = new Matrix4().compose(position, world_rotation, new Vector3(1, 1, 1))

      const bone = new Bone()
      bone.name = MIXAMO_NAME_PREFIX + rule.name

      const local_matrix = rule.parent === null
        ? world_matrix.clone()
        : new Matrix4().copy(world_matrices.get(rule.parent) as Matrix4).invert().multiply(world_matrix)
      local_matrix.decompose(bone.position, bone.quaternion, bone.scale)
      bone.scale.set(1, 1, 1) // the rig is built without scale; drop float noise from decompose

      if (rule.parent !== null) {
        (bones.get(rule.parent) as Bone).add(bone)
      }

      bones.set(rule.name, bone)
      rest_world_rotations.set(rule.name, world_rotation)
      world_matrices.set(rule.name, world_matrix)
    })

    const root_bone = bones.get('Hips') as Bone
    root_bone.updateMatrixWorld(true)

    return { root_bone, bones, rest_world_rotations, source_bone_names: new Map() }
  }

  private static world_rotation_for (
    rule: MixamoBoneRule,
    position: Vector3,
    joint_positions: Map<string, Vector3>,
    rest_world_rotations: Map<string, Quaternion>
  ): Quaternion {
    const parent_rotation = rule.parent !== null ? rest_world_rotations.get(rule.parent) : undefined
    const y_axis = this.aim_direction(rule, position, joint_positions)

    if (y_axis === null) {
      // end bones keep the parent's orientation
      return parent_rotation !== undefined ? parent_rotation.clone() : new Quaternion()
    }

    // The roll axis is the reference direction with its component along Y removed. If the
    // bone points almost straight along the reference, fall back to the parent's same axis
    // so the roll stays continuous down the chain.
    const local_roll_axis = rule.roll.axis === 'x' ? new Vector3(1, 0, 0) : new Vector3(0, 0, 1)
    let roll_axis = this.perpendicular_part(AXIS_REFERENCES[rule.roll.toward], y_axis)
    if (roll_axis.lengthSq() < 1e-6 && parent_rotation !== undefined) {
      roll_axis = this.perpendicular_part(local_roll_axis.applyQuaternion(parent_rotation), y_axis)
    }
    roll_axis.normalize()

    // right-handed: X cross Y = Z, Y cross Z = X
    const x_axis = rule.roll.axis === 'x' ? roll_axis : new Vector3().crossVectors(y_axis, roll_axis).normalize()
    const z_axis = rule.roll.axis === 'z' ? roll_axis : new Vector3().crossVectors(x_axis, y_axis).normalize()
    const basis = new Matrix4().makeBasis(x_axis, y_axis, z_axis)
    return new Quaternion().setFromRotationMatrix(basis)
  }

  /** @returns the Y axis direction, or null when the bone keeps its parent's orientation */
  private static aim_direction (rule: MixamoBoneRule, position: Vector3, joint_positions: Map<string, Vector3>): Vector3 | null {
    if (rule.aim === 'world_up') return WORLD_UP.clone()
    if (rule.aim === 'parent') return null

    for (const target of rule.aim) {
      if (target === 'parent') return null

      const target_position = joint_positions.get(target)
      if (target_position === undefined) continue

      const direction = new Vector3().subVectors(target_position, position)
      if (direction.lengthSq() > 1e-12) return direction.normalize()
    }

    return null
  }

  private static perpendicular_part (vector: Vector3, unit_axis: Vector3): Vector3 {
    return vector.clone().sub(unit_axis.clone().multiplyScalar(vector.dot(unit_axis)))
  }
}
