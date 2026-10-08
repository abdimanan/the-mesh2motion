import { FbxExportPreset } from './DownloadSettings.ts'

type FbxAxis = 'X' | 'Y' | 'Z' | '-X' | '-Y' | '-Z'

// subset of the exporter's FBXExportOptions, which the package does not export
export interface FbxPresetExportOptions {
  preset: 'threejs' | 'unity' | 'unreal' | 'blender' | 'maya'
  axisUp?: FbxAxis
  axisForward?: FbxAxis
  unitScale?: number
}

/**
 * Translates the coordinate preset picked in the download settings into the options the
 * FBX exporter understands.
 *
 * Blender needs two overrides on top of the exporter's own 'blender' preset:
 * - unitScale 100 (from the preset): three.js works in meters, but an FBX UnitScaleFactor
 *   of 1 means centimeters, so without it Blender imports the rig at 1/100th of its size.
 * - axisForward '-Z': the exporter's 'Z' writes FrontAxisSign/CoordAxisSign -1, which makes
 *   Blender turn the character 180 degrees compared to a Mixamo file. '-Z' writes +1/+1,
 *   the same axis declaration Mixamo uses.
 */
export function fbx_exporter_options_for_preset (fbx_export_preset: FbxExportPreset): FbxPresetExportOptions {
  if (fbx_export_preset === FbxExportPreset.Blender) {
    return { preset: 'blender', axisForward: '-Z' }
  }

  return { preset: fbx_export_preset }
}
