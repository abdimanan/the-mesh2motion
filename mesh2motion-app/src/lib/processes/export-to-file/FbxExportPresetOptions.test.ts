import { describe, it, expect } from 'vitest'
import { Bone, Scene } from 'three'
import { FBXExporter } from '@comfyorg/fbx-exporter-three'
import { BinaryParser } from '../../io/fbx/BinaryParser'
import { FbxExportPreset } from './DownloadSettings'
import { fbx_exporter_options_for_preset } from './FbxExportPresetOptions'

async function export_global_settings (fbx_export_preset: FbxExportPreset): Promise<Record<string, { value: number }>> {
  const scene = new Scene()
  const hips = new Bone()
  hips.name = 'Hips'
  scene.add(hips)

  const bytes = await new FBXExporter().parseAsync(scene, fbx_exporter_options_for_preset(fbx_export_preset))
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer
  return new BinaryParser().parse(buffer).GlobalSettings
}

describe('fbx_exporter_options_for_preset', () => {
  it('passes Unreal and Unity straight through to the exporter presets', () => {
    expect(fbx_exporter_options_for_preset(FbxExportPreset.Unreal)).toEqual({ preset: 'unreal' })
    expect(fbx_exporter_options_for_preset(FbxExportPreset.Unity)).toEqual({ preset: 'unity' })
  })

  it('writes Blender files in centimeters so the rig imports at its real size', async () => {
    const settings = await export_global_settings(FbxExportPreset.Blender)

    // three.js scenes are in meters, and FBX unit 1 means 1 cm
    expect(settings.UnitScaleFactor.value).toBe(100)
  })

  it('declares the same axes as a Mixamo file so Blender does not turn the rig around', async () => {
    const settings = await export_global_settings(FbxExportPreset.Blender)

    // Mixamo: Y up, Z front, X coord, all positive
    expect(settings.UpAxis.value).toBe(1)
    expect(settings.UpAxisSign.value).toBe(1)
    expect(settings.FrontAxis.value).toBe(2)
    expect(settings.FrontAxisSign.value).toBe(1)
    expect(settings.CoordAxis.value).toBe(0)
    expect(settings.CoordAxisSign.value).toBe(1)
  })
})
