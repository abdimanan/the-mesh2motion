import { readFileSync } from 'node:fs'
import {
  AnimationClip, type Bone, BoxGeometry, Float32BufferAttribute, MeshBasicMaterial, type Object3D, Quaternion,
  QuaternionKeyframeTrack, Skeleton, SkinnedMesh, Uint16BufferAttribute, Vector3, VectorKeyframeTrack
} from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

export interface Mesh2MotionTestHuman {
  scene: Object3D
  bones: Bone[]
  skinned_mesh: SkinnedMesh
}

/** The real Mesh2Motion human rig, bound to a small mesh the way the Create page binds it. */
export async function load_mesh2motion_test_human (): Promise<Mesh2MotionTestHuman> {
  const buffer = readFileSync('static/rigs/rig-human.glb')

  // allocate inside this realm. A Node ArrayBuffer fails GLTFLoader's
  // `data instanceof ArrayBuffer` check under jsdom and gets parsed as JSON instead
  const array_buffer = new ArrayBuffer(buffer.byteLength)
  new Uint8Array(array_buffer).set(buffer)

  const scene: Object3D = await new Promise((resolve, reject) => {
    new GLTFLoader().parse(array_buffer, '', (gltf) => resolve(gltf.scene), reject)
  })

  const bones: Bone[] = []
  scene.traverse((child) => { if ((child as Bone).isBone === true) bones.push(child as Bone) })

  const geometry = new BoxGeometry(1, 1, 1)
  const vertex_count = geometry.attributes.position.count
  geometry.setAttribute('skinIndex', new Uint16BufferAttribute(new Uint16Array(vertex_count * 4), 4))
  geometry.setAttribute('skinWeight', new Float32BufferAttribute(
    Float32Array.from({ length: vertex_count * 4 }, (_, index) => (index % 4 === 0 ? 1 : 0)), 4))
  const skinned_mesh = new SkinnedMesh(geometry, new MeshBasicMaterial())
  scene.add(skinned_mesh)
  scene.updateMatrixWorld(true)
  skinned_mesh.bind(new Skeleton(bones))

  return { scene, bones, skinned_mesh }
}

function rotated (bone: Bone, axis: Vector3, angle: number): number[] {
  return bone.quaternion.clone().multiply(new Quaternion().setFromAxisAngle(axis, angle)).toArray()
}

/** A one second clip that bends an arm and a leg, twists the spine and moves the root and pelvis. */
export function make_test_clip (bones: Bone[]): AnimationClip {
  const bone = (name: string): Bone => bones.find(candidate => candidate.name === name) as Bone
  const times = [0, 0.5, 1]
  const quaternion_track = (name: string, axis: Vector3, angles: number[]): QuaternionKeyframeTrack =>
    new QuaternionKeyframeTrack(`${name}.quaternion`, times, angles.flatMap(angle => rotated(bone(name), axis, angle)))

  const pelvis = bone('pelvis').position
  const root = bone('root').position

  return new AnimationClip('Test_Move', 1, [
    quaternion_track('upperarm_l', new Vector3(0, 0, 1), [0, 0.9, 0.3]),
    quaternion_track('lowerarm_l', new Vector3(1, 0, 0), [0, -0.7, -1.2]),
    quaternion_track('thigh_r', new Vector3(1, 0, 0), [0, 0.6, -0.4]),
    quaternion_track('spine_02', new Vector3(0, 1, 0), [0, 0.3, -0.2]),
    new VectorKeyframeTrack('pelvis.position', times, [
      pelvis.x, pelvis.y, pelvis.z,
      pelvis.x + 0.05, pelvis.y - 0.04, pelvis.z,
      pelvis.x, pelvis.y, pelvis.z + 0.02
    ]),
    // root motion: the whole character travels forward
    new VectorKeyframeTrack('root.position', times, [
      root.x, root.y, root.z,
      root.x, root.y + 0.2, root.z,
      root.x, root.y + 0.4, root.z
    ])
  ])
}
