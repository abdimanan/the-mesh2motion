import { describe, it, expect, beforeEach } from 'vitest'
import { DOMUtilities } from '../../DOMUtilities'
import { SkeletonType } from '../../enums/SkeletonType'
import { BoneNamingStructure, DownloadSettings, ExportContents, ExportFormat, FbxExportPreset } from './DownloadSettings'

function select_radio (name: string, value: string): void {
  const radio = document.querySelector<HTMLInputElement>(`input[name="${name}"][value="${value}"]`)
  if (radio === null) throw new Error(`no ${name} radio for ${value}`)
  radio.checked = true
  radio.dispatchEvent(new Event('change', { bubbles: true }))
}

function glb_warning (): HTMLElement {
  return document.querySelector('#download-glb-skeleton-warning') as HTMLElement
}

describe('DownloadSettings', () => {
  let settings: DownloadSettings

  beforeEach(() => {
    document.body.innerHTML = '<div id="download-control-mount"></div>'
    DOMUtilities.populate_download_control(document.querySelector('#download-control-mount') as HTMLElement)
    settings = new DownloadSettings()
  })

  it('offers Unreal, Unity and Blender as FBX presets, with Unreal still the default', () => {
    const preset_values = Array.from(document.querySelectorAll<HTMLInputElement>('input[name="fbx-export-preset"]'))
      .map(radio => radio.value)

    expect(preset_values).toEqual(['unreal', 'unity', 'blender'])
    expect(settings.fbx_export_preset()).toBe(FbxExportPreset.Unreal)
  })

  it('picks up the Blender preset when it is selected', () => {
    select_radio('export-format', ExportFormat.FBX)
    select_radio('fbx-export-preset', FbxExportPreset.Blender)

    expect(settings.fbx_export_preset()).toBe(FbxExportPreset.Blender)
  })

  it('warns only when a GLB is exported without the mesh', () => {
    expect(glb_warning().hidden).toBe(true)

    select_radio('export-contents', ExportContents.Skeleton)
    expect(glb_warning().hidden).toBe(false)

    select_radio('export-format', ExportFormat.FBX)
    expect(glb_warning().hidden).toBe(true)

    select_radio('export-format', ExportFormat.GLB)
    select_radio('export-contents', ExportContents.Full)
    expect(glb_warning().hidden).toBe(true)
  })

  describe('Mixamo skeleton for Blender', () => {
    function mixamo_note (): HTMLElement {
      return document.querySelector('#download-mixamo-blender-note') as HTMLElement
    }

    function pick_fbx_blender_mixamo (): void {
      select_radio('export-format', ExportFormat.FBX)
      select_radio('fbx-export-preset', FbxExportPreset.Blender)
      select_radio('bone-naming-structure', BoneNamingStructure.Mixamo)
    }

    it('turns on for FBX + Blender + Mixamo naming on the human skeleton', () => {
      settings.update_download_settings_ui_visibility(SkeletonType.Human)
      expect(settings.is_mixamo_blender_export()).toBe(false)
      expect(mixamo_note().hidden).toBe(true)

      pick_fbx_blender_mixamo()

      expect(settings.is_mixamo_blender_export()).toBe(true)
      expect(mixamo_note().hidden).toBe(false)
    })

    it('stays off when any of the three options is different', () => {
      settings.update_download_settings_ui_visibility(SkeletonType.Human)
      pick_fbx_blender_mixamo()

      select_radio('fbx-export-preset', FbxExportPreset.Unity)
      expect(settings.is_mixamo_blender_export()).toBe(false)
      select_radio('fbx-export-preset', FbxExportPreset.Blender)
      select_radio('bone-naming-structure', BoneNamingStructure.Default)
      expect(settings.is_mixamo_blender_export()).toBe(false)
      select_radio('bone-naming-structure', BoneNamingStructure.Mixamo)
      select_radio('export-format', ExportFormat.GLB)
      expect(settings.is_mixamo_blender_export()).toBe(false)
      expect(mixamo_note().hidden).toBe(true)
    })

    it('stays off for other skeletons and on pages that switch it off', () => {
      settings.update_download_settings_ui_visibility(SkeletonType.Fox)
      pick_fbx_blender_mixamo()
      expect(settings.is_mixamo_blender_export()).toBe(false)

      settings.update_download_settings_ui_visibility(SkeletonType.Human)
      pick_fbx_blender_mixamo()
      settings.set_mixamo_blender_export_supported(false)
      expect(settings.is_mixamo_blender_export()).toBe(false)
      expect(mixamo_note().hidden).toBe(true)
    })
  })
})
