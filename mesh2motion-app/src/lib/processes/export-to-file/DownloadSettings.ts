import { SkeletonType } from '../../enums/SkeletonType.ts'

export enum BoneNamingStructure {
  Default = 'default',
  Mixamo = 'mixamo'
}

export enum ExportContents {
  Full = 'full',
  Skeleton = 'skeleton'
}

export enum ExportFormat {
  GLB = 'glb',
  FBX = 'fbx'
}

export enum FbxExportPreset {
  Unreal = 'unreal',
  // ThreeJS = 'threejs',
  Unity = 'unity',
  Blender = 'blender'
  // Maya = 'maya'
}

export class DownloadSettings extends EventTarget {
  private selected_bone_naming_structure: BoneNamingStructure = this.get_default_bone_naming_structure()
  private selected_export_contents: ExportContents = this.get_default_export_contents()
  private selected_export_format: ExportFormat = this.get_default_export_format()
  private selected_fbx_export_preset: FbxExportPreset = this.get_default_fbx_export_preset()
  private dom_download_settings_popup: HTMLElement | null = null
  private dom_download_settings_toggle: HTMLButtonElement | null = null
  private dom_download_settings_panel: HTMLElement | null = null
  private dom_bone_naming_section: HTMLElement | null = null
  private dom_bone_naming_group: HTMLElement | null = null
  private dom_export_contents_group: HTMLElement | null = null
  private dom_export_format_group: HTMLElement | null = null
  private dom_fbx_preset_section: HTMLElement | null = null
  private dom_fbx_preset_group: HTMLElement | null = null
  private dom_glb_skeleton_warning: HTMLElement | null = null
  private dom_mixamo_blender_note: HTMLElement | null = null
  private is_human_skeleton: boolean = false
  private mixamo_blender_export_supported: boolean = true

  constructor () {
    super()
    this.initialize_dom_elements()
    this.update_fbx_preset_ui_visibility()
    this.update_glb_skeleton_warning_visibility()
    this.add_event_listeners()
  }

  public bone_naming_structure (): BoneNamingStructure {
    return this.selected_bone_naming_structure
  }

  public export_contents (): ExportContents {
    return this.selected_export_contents
  }

  public export_format (): ExportFormat {
    return this.selected_export_format
  }

  public fbx_export_preset (): FbxExportPreset {
    return this.selected_fbx_export_preset
  }

  /**
   * FBX + Blender + Mixamo bone naming on the human skeleton downloads the standard Mixamo
   * skeleton with the animations converted onto it, so the actions can be mixed with Mixamo
   * clips in Blender's NLA Editor.
   */
  public is_mixamo_blender_export (): boolean {
    return this.mixamo_blender_export_supported &&
      this.is_human_skeleton &&
      this.selected_export_format === ExportFormat.FBX &&
      this.selected_fbx_export_preset === FbxExportPreset.Blender &&
      this.selected_bone_naming_structure === BoneNamingStructure.Mixamo
  }

  // The download settings popup is available for all skeleton types. The bone naming
  // options only apply to the human skeleton, so that section is shown/hidden here while
  // the export contents options remain available regardless of skeleton type.
  public update_download_settings_ui_visibility (skeleton_type: SkeletonType): void {
    // reset to defaults
    this.selected_bone_naming_structure = this.get_default_bone_naming_structure()
    this.set_radio_group_value(this.dom_bone_naming_group, 'bone-naming-structure', this.selected_bone_naming_structure)

    this.selected_export_contents = this.get_default_export_contents()
    this.set_radio_group_value(this.dom_export_contents_group, 'export-contents', this.selected_export_contents)

    this.selected_export_format = this.get_default_export_format()
    this.set_radio_group_value(this.dom_export_format_group, 'export-format', this.selected_export_format)

    this.selected_fbx_export_preset = this.get_default_fbx_export_preset()
    this.set_radio_group_value(this.dom_fbx_preset_group, 'fbx-export-preset', this.selected_fbx_export_preset)

    const is_human_skeleton = skeleton_type === SkeletonType.Human
    this.is_human_skeleton = is_human_skeleton

    // Only the bone naming section is human-only; the popup itself is always available.
    if (this.dom_bone_naming_section !== null) {
      this.dom_bone_naming_section.style.display = is_human_skeleton ? '' : 'none'
    }

    this.update_fbx_preset_ui_visibility()
    this.update_glb_skeleton_warning_visibility()
    this.update_mixamo_blender_note_visibility()
  }

  private initialize_dom_elements (): void {
    this.dom_download_settings_popup = document.querySelector('#download-settings-popup')
    this.dom_download_settings_toggle = document.querySelector('#download-settings-toggle')
    this.dom_download_settings_panel = document.querySelector('#download-settings')
    this.dom_bone_naming_section = document.querySelector('#download-bone-naming-section')
    this.dom_bone_naming_group = document.querySelector('#download-bone-naming-group')
    this.dom_export_contents_group = document.querySelector('#download-export-contents-group')
    this.dom_export_format_group = document.querySelector('#download-export-format-group')
    this.dom_fbx_preset_section = document.querySelector('#download-fbx-preset-section')
    this.dom_fbx_preset_group = document.querySelector('#download-fbx-preset-group')
    this.dom_glb_skeleton_warning = document.querySelector('#download-glb-skeleton-warning')
    this.dom_mixamo_blender_note = document.querySelector('#download-mixamo-blender-note')
  }

  private add_event_listeners (): void {
    // any option can switch the Mixamo-for-Blender download on or off
    this.dom_download_settings_panel?.addEventListener('change', () => {
      this.update_mixamo_blender_note_visibility()
    })

    this.dom_download_settings_toggle?.addEventListener('click', () => {
      this.set_popup_visibility(this.dom_download_settings_panel?.hidden !== false)
    })

    document.addEventListener('click', (event: MouseEvent) => {
      if (this.dom_download_settings_panel?.hidden !== false) {
        return
      }

      const clicked_element = event.target as Node | null
      if (clicked_element === null) {
        return
      }

      if (this.dom_download_settings_popup?.contains(clicked_element) !== true) {
        this.set_popup_visibility(false)
      }
    })

    document.addEventListener('keydown', (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        this.set_popup_visibility(false)
      }
    })

    this.dom_bone_naming_group?.addEventListener('change', (event: Event) => {
      const selected_radio = event.target as HTMLInputElement | null

      if (selected_radio === null || selected_radio.name !== 'bone-naming-structure') {
        return
      }

      if (this.is_bone_naming_structure(selected_radio.value)) {
        this.selected_bone_naming_structure = selected_radio.value
      } else {
        this.selected_bone_naming_structure = this.get_default_bone_naming_structure()
      }

      this.dispatchEvent(new CustomEvent('bone-naming-structure-changed', {
        detail: { boneNamingStructure: this.selected_bone_naming_structure }
      }))
    })

    this.dom_export_contents_group?.addEventListener('change', (event: Event) => {
      const selected_radio = event.target as HTMLInputElement | null

      if (selected_radio === null || selected_radio.name !== 'export-contents') {
        return
      }

      if (this.is_export_contents(selected_radio.value)) {
        this.selected_export_contents = selected_radio.value
      } else {
        this.selected_export_contents = this.get_default_export_contents()
      }

      this.dispatchEvent(new CustomEvent('export-contents-changed', {
        detail: { exportContents: this.selected_export_contents }
      }))

      this.update_glb_skeleton_warning_visibility()
    })

    this.dom_export_format_group?.addEventListener('change', (event: Event) => {
      const selected_radio = event.target as HTMLInputElement | null

      if (selected_radio === null || selected_radio.name !== 'export-format') {
        return
      }

      if (this.is_export_format(selected_radio.value)) {
        this.selected_export_format = selected_radio.value
      } else {
        this.selected_export_format = this.get_default_export_format()
      }

      this.dispatchEvent(new CustomEvent('export-format-changed', {
        detail: { exportFormat: this.selected_export_format }
      }))

      this.update_fbx_preset_ui_visibility()
      this.update_glb_skeleton_warning_visibility()
    })

    this.dom_fbx_preset_group?.addEventListener('change', (event: Event) => {
      const selected_radio = event.target as HTMLInputElement | null

      if (selected_radio === null || selected_radio.name !== 'fbx-export-preset') {
        return
      }

      if (this.is_fbx_export_preset(selected_radio.value)) {
        this.selected_fbx_export_preset = selected_radio.value
      } else {
        this.selected_fbx_export_preset = this.get_default_fbx_export_preset()
      }

      this.dispatchEvent(new CustomEvent('fbx-export-preset-changed', {
        detail: { fbxExportPreset: this.selected_fbx_export_preset }
      }))
    })
  }

  private update_fbx_preset_ui_visibility (): void {
    if (this.dom_fbx_preset_section === null) {
      return
    }

    const should_show_fbx_preset = this.selected_export_format === ExportFormat.FBX
    this.dom_fbx_preset_section.hidden = !should_show_fbx_preset
  }

  // glTF only treats nodes as joints when a skin references them. A skeleton-only GLB has
  // no mesh and so no skin, which Blender imports as one empty per bone.
  private update_glb_skeleton_warning_visibility (): void {
    if (this.dom_glb_skeleton_warning === null) {
      return
    }

    const is_glb_skeleton_only = this.selected_export_format === ExportFormat.GLB &&
      this.selected_export_contents === ExportContents.Skeleton
    this.dom_glb_skeleton_warning.hidden = !is_glb_skeleton_only
  }

  /** Pages whose export cannot produce the Mixamo-for-Blender download switch it off. */
  public set_mixamo_blender_export_supported (is_supported: boolean): void {
    this.mixamo_blender_export_supported = is_supported
    this.update_mixamo_blender_note_visibility()
  }

  private update_mixamo_blender_note_visibility (): void {
    if (this.dom_mixamo_blender_note === null) {
      return
    }

    this.dom_mixamo_blender_note.hidden = !this.is_mixamo_blender_export()
  }

  private set_popup_visibility (is_visible: boolean): void {
    if (this.dom_download_settings_panel !== null) {
      this.dom_download_settings_panel.hidden = !is_visible
    }

    if (this.dom_download_settings_toggle !== null) {
      this.dom_download_settings_toggle.setAttribute('aria-expanded', is_visible ? 'true' : 'false')
    }
  }

  private set_radio_group_value (group: HTMLElement | null, name: string, value: string): void {
    const option_radio = group?.querySelector<HTMLInputElement>(`input[name="${name}"][value="${value}"]`)
    if (option_radio !== null && option_radio !== undefined) {
      option_radio.checked = true
    }
  }

  private is_bone_naming_structure (value: string): value is BoneNamingStructure {
    return Object.values(BoneNamingStructure).includes(value as BoneNamingStructure)
  }

  private is_export_contents (value: string): value is ExportContents {
    return Object.values(ExportContents).includes(value as ExportContents)
  }

  private is_export_format (value: string): value is ExportFormat {
    return Object.values(ExportFormat).includes(value as ExportFormat)
  }

  private is_fbx_export_preset (value: string): value is FbxExportPreset {
    return Object.values(FbxExportPreset).includes(value as FbxExportPreset)
  }

  private get_default_fbx_export_preset (): FbxExportPreset {
    return this.get_first_enum_value(FbxExportPreset)
  }

  private get_default_bone_naming_structure (): BoneNamingStructure {
    return this.get_first_enum_value(BoneNamingStructure)
  }

  private get_default_export_contents (): ExportContents {
    return this.get_first_enum_value(ExportContents)
  }

  private get_default_export_format (): ExportFormat {
    return this.get_first_enum_value(ExportFormat)
  }

  private get_first_enum_value<T extends string> (enum_object: Record<string, T>): T {
    const enum_values = Object.values(enum_object)
    if (enum_values.length === 0) {
      throw new Error('Enum has no values')
    }

    return enum_values[0]
  }
}
