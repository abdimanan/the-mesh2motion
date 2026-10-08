import { describe, it, expect, vi } from 'vitest'
import { BinaryParser } from '../../io/fbx/BinaryParser'
import { type DownloadSettings } from './DownloadSettings'
import { StepExportToFile } from './StepExportToFile'
import { load_mesh2motion_test_human, make_test_clip } from './mixamo/mixamo-test-helpers'

interface ParsedNode { propertyList: [number, string, string] }

describe('StepExportToFile.export with the Mixamo skeleton for Blender', () => {
  it('downloads the standard Mixamo skeleton with the clips and leaves the scene untouched', async () => {
    const human = await load_mesh2motion_test_human()
    const clip = make_test_clip(human.bones)
    const bone_names_before = human.bones.map(bone => bone.name)
    const root_parent_before = human.bones[0].parent

    const step = new StepExportToFile()
    const saved_files: Array<{ bytes: Uint8Array, name: string }> = []
    const step_internals = step as unknown as { save_uint8_array: (bytes: Uint8Array, name: string) => void }
    vi.spyOn(step_internals, 'save_uint8_array').mockImplementation((bytes, name) => { saved_files.push({ bytes, name }) })

    step.set_animation_clips_to_export([clip], [{ animation_index: 0, mirror_export_mode: 'none' }] as never)
    const download_settings = { is_mixamo_blender_export: () => true } as unknown as DownloadSettings
    await step.export([human.skinned_mesh], 'exported-model', download_settings)

    expect(saved_files.map(file => file.name)).toEqual(['exported-model.fbx'])

    const bytes = saved_files[0].bytes
    const tree = new BinaryParser().parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    const models = Object.values(tree.Objects.Model as Record<string, ParsedNode>)
    expect(models).toHaveLength(65)
    expect(models.map(model => model.propertyList[1])).toContain('mixamorig:Hips')
    expect(Object.keys(tree.Objects.AnimationStack)).toHaveLength(1)

    // the Mesh2Motion skeleton is not renamed or moved by this export
    expect(human.bones.map(bone => bone.name)).toEqual(bone_names_before)
    expect(human.bones[0].parent).toBe(root_parent_before)
  })
})
