/**
 * The standard Mixamo skeleton (the one Mixamo's default character, Y Bot, and its
 * "Without Skin" animation downloads use): world joint positions in centimeters and rest
 * world rotations (x, y, z, w) of its 65 bones.
 *
 * Frame: Y up, the character faces +Z and +X is its left, which is both the Mixamo FBX
 * file frame and the three.js frame. Measured from a Mixamo T-pose download; a Y Bot
 * character download has the identical skeleton (0.000 degrees, < 0.01 cm).
 *
 * Exporting onto this exact skeleton is what lets Mesh2Motion actions be mixed with Mixamo
 * actions on the same armature in Blender's NLA Editor.
 */
export interface MixamoJointTransform {
  position: [number, number, number]
  rotation: [number, number, number, number]
}

export const MIXAMO_STANDARD_SKELETON: Record<string, MixamoJointTransform> = {
  Hips: { position: [0, 99.7919, 0], rotation: [0, -0.0000017, 0.0000436, 1] },
  Spine: { position: [0, 109.7154, -1.2273], rotation: [-0.0607306, -0.0000048, 0.0000495, 0.9981542] },
  LeftUpLeg: { position: [9.1245, 93.1355, -0.0554], rotation: [-0.0000191, 0.0063503, -0.9999753, 0.0030136] },
  RightUpLeg: { position: [-9.1244, 93.1355, -0.0554], rotation: [-0.0000191, -0.0063337, 0.9999754, 0.0030136] },
  Spine1: { position: [-0.0011, 121.3609, -2.6497], rotation: [-0.0605346, -0.0000053, 0.00004, 0.9981661] },
  Spine2: { position: [-0.0022, 134.721, -4.2761], rotation: [-0.0028274, -0.0000009, 0.0000435, 0.999996] },
  Neck: { position: [-0.0035, 149.7535, -3.4832], rotation: [0, -0.0000008, 0.0000435, 1] },
  LeftShoulder: { position: [6.1028, 143.832, -3.5705], rotation: [0.4526011, 0.5432794, -0.5526855, 0.4410652] },
  RightShoulder: { position: [-6.1087, 143.831, -3.5705], rotation: [0.4525813, -0.5432958, 0.55267, 0.4410846] },
  Head: { position: [-0.0044, 160.0753, -0.3408], rotation: [0, -0.0000008, 0.0000435, 1] },
  HeadTop_End: { position: [-0.0058, 178.55, 6.2956], rotation: [0, -0.0000008, 0.0000435, 1] },
  LeftArm: { position: [18.7579, 143.5656, -6.1714], rotation: [0.5000001, 0.5000001, -0.4999999, 0.4999999] },
  LeftForeArm: { position: [46.1626, 143.5656, -6.1714], rotation: [0.5000001, 0.5000001, -0.4999999, 0.4999999] },
  LeftHand: { position: [73.7771, 143.5656, -6.1714], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandThumb1: { position: [77.5659, 141.3985, -3.1684], rotation: [0.6772209, 0.2034012, -0.5147608, 0.4847898] },
  LeftHandIndex1: { position: [86.0437, 143.3338, -3.3494], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandMiddle1: { position: [86.5526, 143.5656, -6.1714], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandRing1: { position: [85.9241, 143.5756, -8.388], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandPinky1: { position: [84.6853, 143.3395, -10.8972], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandThumb2: { position: [81.2413, 139.2764, -1.0464], rotation: [0.6772209, 0.2034012, -0.5147608, 0.4847898] },
  LeftHandThumb3: { position: [84.6357, 137.3167, 0.9134], rotation: [0.6772209, 0.2034012, -0.5147608, 0.4847898] },
  LeftHandThumb4: { position: [87.3151, 135.7697, 2.4603], rotation: [0.7538182, 0.208638, -0.3911467, 0.4850079] },
  LeftHandIndex2: { position: [89.9357, 143.3338, -3.3494], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandIndex3: { position: [93.3509, 143.3338, -3.3494], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandIndex4: { position: [96.4289, 143.3338, -3.3494], rotation: [0.5020086, 0.5019851, -0.4979842, 0.4980061] },
  LeftHandMiddle2: { position: [90.1666, 143.5656, -6.1714], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandMiddle3: { position: [93.6264, 143.5656, -6.1714], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandMiddle4: { position: [97.3066, 143.5656, -6.1714], rotation: [0.5019564, 0.5026123, -0.4980315, 0.4973784] },
  LeftHandRing2: { position: [89.5253, 143.5756, -8.388], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandRing3: { position: [92.8326, 143.5756, -8.388], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandRing4: { position: [96.4927, 143.5756, -8.388], rotation: [0.5040737, 0.503295, -0.4959069, 0.4966691] },
  LeftHandPinky2: { position: [88.822, 143.3395, -10.8972], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandPinky3: { position: [91.4168, 143.3395, -10.8972], rotation: [0.4999998, 0.4999998, -0.5000002, 0.5000002] },
  LeftHandPinky4: { position: [94.3407, 143.3395, -10.8972], rotation: [0.5017573, 0.5023335, -0.498233, 0.497659] },
  RightArm: { position: [-18.7637, 143.5655, -6.1714], rotation: [0.5000001, -0.5000001, 0.4999999, 0.4999999] },
  RightForeArm: { position: [-46.1684, 143.5655, -6.1714], rotation: [0.5000001, -0.5000001, 0.4999999, 0.4999999] },
  RightHand: { position: [-73.7829, 143.5655, -6.1714], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandThumb1: { position: [-77.5717, 141.3984, -3.1684], rotation: [0.6772207, -0.203401, 0.5147611, 0.4847899] },
  RightHandIndex1: { position: [-86.0495, 143.3337, -3.3494], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandMiddle1: { position: [-86.5584, 143.5655, -6.1714], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandRing1: { position: [-85.9299, 143.5755, -8.388], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandPinky1: { position: [-84.6911, 143.3394, -10.8972], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandThumb2: { position: [-81.2472, 139.2764, -1.0464], rotation: [0.6772207, -0.203401, 0.5147611, 0.4847899] },
  RightHandThumb3: { position: [-84.6416, 137.3166, 0.9133], rotation: [0.6772207, -0.203401, 0.5147611, 0.4847899] },
  RightHandThumb4: { position: [-87.321, 135.7697, 2.4603], rotation: [0.7545371, -0.2091021, 0.3899223, 0.4846758] },
  RightHandIndex2: { position: [-89.9415, 143.3337, -3.3494], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandIndex3: { position: [-93.3567, 143.3337, -3.3494], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandIndex4: { position: [-96.4347, 143.3337, -3.3494], rotation: [0.5026189, -0.5040664, 0.4972849, 0.4959829] },
  RightHandMiddle2: { position: [-90.1724, 143.5655, -6.1714], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandMiddle3: { position: [-93.6322, 143.5655, -6.1714], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandMiddle4: { position: [-97.3124, 143.5655, -6.1714], rotation: [0.5041636, -0.5025071, 0.4957609, 0.4975206] },
  RightHandRing2: { position: [-89.5311, 143.5755, -8.388], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandRing3: { position: [-92.8384, 143.5755, -8.388], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandRing4: { position: [-96.4985, 143.5755, -8.388], rotation: [0.5039113, -0.5036723, 0.495998, 0.4963603] },
  RightHandPinky2: { position: [-88.8278, 143.3394, -10.8972], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandPinky3: { position: [-91.4226, 143.3394, -10.8972], rotation: [0.4999998, -0.4999998, 0.5000002, 0.5000002] },
  RightHandPinky4: { position: [-94.3465, 143.3394, -10.8972], rotation: [0.5030858, -0.5053743, 0.4967932, 0.4946696] },
  LeftLeg: { position: [9.3692, 52.5401, -0.571], rotation: [-0.000071, -0.024463, 0.9996965, 0.0029087] },
  LeftFoot: { position: [9.1245, 10.4922, -2.6301], rotation: [0.0134599, -0.51986, -0.8538593, 0.0221078] },
  LeftToeBase: { position: [9.498, 3.2836, 11.3365], rotation: [0.0016496, 0.7007884, 0.7132733, 0.0115789] },
  LeftToe_End: { position: [9.356, 3.1084, 21.3339], rotation: [0.0016496, 0.7007884, 0.7132733, 0.0115789] },
  RightLeg: { position: [-9.3691, 52.5401, -0.5697], rotation: [-0.0000712, 0.0244796, -0.9996961, 0.0029087] },
  RightFoot: { position: [-9.1244, 10.4923, -2.6302], rotation: [0.0134606, 0.51986, 0.8538593, 0.0221084] },
  RightToeBase: { position: [-9.498, 3.2837, 11.3364], rotation: [0.0013616, -0.700801, -0.7132664, 0.0112775] },
  RightToe_End: { position: [-9.3562, 3.1087, 21.3338], rotation: [0.0013616, -0.700801, -0.7132664, 0.0112775] }
}
