import { describe, it, expect } from 'vitest'
import { BinaryParser } from '../../../io/fbx/BinaryParser'
import { MixamoFbxExportService } from './MixamoFbxExportService'
import { load_mesh2motion_test_human, make_test_clip } from './mixamo-test-helpers'

interface ParsedNode { propertyList: [number, string, string] }

async function export_and_parse (): Promise<ReturnType<BinaryParser['parse']>> {
  const human = await load_mesh2motion_test_human()
  const clip = make_test_clip(human.bones)
  const second_clip = clip.clone()
  second_clip.name = 'Test_Move_2'

  const bytes = await MixamoFbxExportService.export([human.skinned_mesh], [clip, second_clip])
  return new BinaryParser().parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
}

describe('MixamoFbxExportService.export', () => {
  it('writes 65 mixamorig bones with colons and nothing else', async () => {
    const tree = await export_and_parse()
    const models = Object.values(tree.Objects.Model as Record<string, ParsedNode>)

    expect(models).toHaveLength(65)
    expect(models.every(model => model.propertyList[2] === 'LimbNode')).toBe(true)
    const names = models.map(model => model.propertyList[1])
    expect(names).toContain('mixamorig:Hips')
    expect(names).toContain('mixamorig:LeftHandThumb4')
    expect(names.every(name => name.startsWith('mixamorig:'))).toBe(true)
  })

  it('hangs Hips straight off the scene root', async () => {
    const tree = await export_and_parse()
    const models = tree.Objects.Model as Record<string, ParsedNode>
    const roots = (tree.Connections.connections as Array<[number, number]>)
      .filter(([child, parent]) => models[String(child)] !== undefined && parent === 0)
      .map(([child]) => models[String(child)].propertyList[1])

    expect(roots).toEqual(['mixamorig:Hips'])
  })

  it('declares centimeters, Y up and the same axis signs as a Mixamo file', async () => {
    const settings = (await export_and_parse()).GlobalSettings

    expect(settings.UnitScaleFactor.value).toBe(1)
    expect([settings.UpAxis.value, settings.UpAxisSign.value]).toEqual([1, 1])
    expect([settings.FrontAxis.value, settings.FrontAxisSign.value]).toEqual([2, 1])
    expect([settings.CoordAxis.value, settings.CoordAxisSign.value]).toEqual([0, 1])
    expect(settings.TimeMode.value).toBe(6) // 30 fps
  })

  it('writes one take per clip, rotations on 52 bones and translation on Hips only', async () => {
    const tree = await export_and_parse()
    const models = tree.Objects.Model as Record<string, ParsedNode>
    const connections = tree.Connections.connections as Array<[number, number, string?]>

    expect(Object.keys(tree.Objects.AnimationStack)).toHaveLength(2)

    const animated = (property: string): string[] => connections
      .filter(([, , relationship]) => relationship === property)
      .map(([, parent]) => models[String(parent)].propertyList[1])

    expect(new Set(animated('Lcl Rotation')).size).toBe(52)
    expect(new Set(animated('Lcl Translation'))).toEqual(new Set(['mixamorig:Hips']))
    expect(animated('Lcl Scaling')).toEqual([])
  })
})
