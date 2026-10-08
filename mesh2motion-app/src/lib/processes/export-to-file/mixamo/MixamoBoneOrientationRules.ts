/**
 * The Mixamo skeleton: its 65 bones, their hierarchy, and the rule Mixamo uses to orient
 * each bone.
 *
 * Blender stores keyframes relative to each bone's own axes, so a Mesh2Motion action only
 * plays correctly on a Mixamo armature (and can be mixed with Mixamo clips in the NLA
 * Editor) when every bone has the same axes Mixamo would have given it. Mixamo's auto-rigger
 * derives those axes from the joint positions, so the same rule applied to Mesh2Motion's
 * joints gives a matching skeleton, whatever proportions the user edited it to.
 *
 * The rule was measured on a Mixamo "Without Skin" download, in the file's Y-up frame where
 * the character faces +Z and +X is the character's left (the same frame three.js uses):
 * - Y axis points along the bone: at the aim target below
 * - the roll is set by pointing one other axis (X for most bones, Z for the legs) at a
 *   world direction, made perpendicular to Y
 * - the third axis completes a right-handed frame
 * Every animated bone matches Mixamo to within 0.3 degrees with this rule.
 */

export type MixamoAxisReference = '+X' | '-X' | '+Z' | '-Z'

/** Which local axis is pointed at the reference direction to fix the bone's roll. */
export interface MixamoRollRule {
  axis: 'x' | 'z'
  toward: MixamoAxisReference
}

/**
 * Where a bone's Y axis points.
 * - 'world_up': straight up (Hips, Spine2, Neck, Head)
 * - a bone name: at that child's joint. Several names are tried in order, so a hand with
 *   no middle finger still aims down the fingers it has
 * - 'parent': keep the parent's orientation. Mixamo's end bones (finger tips, Toe_End) are
 *   never animated and sit along their parent's axis
 */
export type MixamoAimTarget = 'world_up' | 'parent' | string[]

export interface MixamoBoneRule {
  name: string // Mixamo bone name without the "mixamorig:" prefix
  parent: string | null
  aim: MixamoAimTarget
  roll: MixamoRollRule
}

export const MIXAMO_NAME_PREFIX = 'mixamorig:'

const TORSO: MixamoRollRule = { axis: 'x', toward: '+X' }
const LEFT_ARM: MixamoRollRule = { axis: 'x', toward: '-Z' } // X points back
const RIGHT_ARM: MixamoRollRule = { axis: 'x', toward: '+Z' } // X points forward
// Mixamo keeps the leg's Z axis facing forward. The foot tilts down towards the toes, so
// pointing X sideways instead would be 2.6 degrees off there
const LEG: MixamoRollRule = { axis: 'z', toward: '+Z' }
// the toes point forward, so Z cannot face forward too
const TOES: MixamoRollRule = { axis: 'x', toward: '-X' }

function finger_rules (side: 'Left' | 'Right', finger: string, roll: MixamoRollRule): MixamoBoneRule[] {
  const hand = `${side}Hand`
  const bone = (index: number): string => `${side}Hand${finger}${index}`

  return [
    { name: bone(1), parent: hand, aim: [bone(2)], roll },
    { name: bone(2), parent: bone(1), aim: [bone(3)], roll },
    { name: bone(3), parent: bone(2), aim: [bone(4), 'parent'], roll },
    { name: bone(4), parent: bone(3), aim: 'parent', roll }
  ]
}

function arm_rules (side: 'Left' | 'Right', roll: MixamoRollRule): MixamoBoneRule[] {
  return [
    { name: `${side}Shoulder`, parent: 'Spine2', aim: [`${side}Arm`], roll },
    { name: `${side}Arm`, parent: `${side}Shoulder`, aim: [`${side}ForeArm`], roll },
    { name: `${side}ForeArm`, parent: `${side}Arm`, aim: [`${side}Hand`], roll },
    // the hand points down the middle finger. Simplified hands may not have one
    {
      name: `${side}Hand`,
      parent: `${side}ForeArm`,
      aim: [`${side}HandMiddle1`, `${side}HandIndex1`, `${side}HandRing1`, 'parent'],
      roll
    },
    ...['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'].flatMap(finger => finger_rules(side, finger, roll))
  ]
}

function leg_rules (side: 'Left' | 'Right'): MixamoBoneRule[] {
  return [
    { name: `${side}UpLeg`, parent: 'Hips', aim: [`${side}Leg`], roll: LEG },
    { name: `${side}Leg`, parent: `${side}UpLeg`, aim: [`${side}Foot`], roll: LEG },
    { name: `${side}Foot`, parent: `${side}Leg`, aim: [`${side}ToeBase`], roll: LEG },
    { name: `${side}ToeBase`, parent: `${side}Foot`, aim: [`${side}Toe_End`, 'parent'], roll: TOES },
    { name: `${side}Toe_End`, parent: `${side}ToeBase`, aim: 'parent', roll: TOES }
  ]
}

/** Parents always come before their children. */
export const MIXAMO_BONE_RULES: MixamoBoneRule[] = [
  { name: 'Hips', parent: null, aim: 'world_up', roll: TORSO },
  { name: 'Spine', parent: 'Hips', aim: ['Spine1'], roll: TORSO },
  { name: 'Spine1', parent: 'Spine', aim: ['Spine2'], roll: TORSO },
  { name: 'Spine2', parent: 'Spine1', aim: 'world_up', roll: TORSO },
  { name: 'Neck', parent: 'Spine2', aim: 'world_up', roll: TORSO },
  { name: 'Head', parent: 'Neck', aim: 'world_up', roll: TORSO },
  { name: 'HeadTop_End', parent: 'Head', aim: 'world_up', roll: TORSO },
  ...arm_rules('Left', LEFT_ARM),
  ...arm_rules('Right', RIGHT_ARM),
  ...leg_rules('Left'),
  ...leg_rules('Right')
]

/** A Mixamo skeleton cannot be built without these. Fingers, tips and toes are optional. */
export const MIXAMO_REQUIRED_BONES: string[] = [
  'Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
  'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
  'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand',
  'LeftUpLeg', 'LeftLeg', 'LeftFoot',
  'RightUpLeg', 'RightLeg', 'RightFoot'
]
