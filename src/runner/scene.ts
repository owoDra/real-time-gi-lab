// Scene names of the runners -> SceneSpec. The platform supplies Sponza (glTF JSON, binary buffer, image uploader).
import { parseGltf } from '../core/gltf.ts';
import type { ImageUploader } from '../core/scene_gpu.ts';
import { leakRoom, sponzaScene, townScene, withBuildingMotion, type SceneSpec } from '../core/scenes.ts';
import { DEFAULT_VOX, triangleTable } from '../core/voxel.ts';
import { DEFAULT_LOD0_CELL, withWorld } from '../core/world.ts';

export async function loadScene(sceneArg: string, sponza: () => Promise<{ json: any; bin: ArrayBuffer; upload: ImageUploader }>,
  lod0Cell = DEFAULT_LOD0_CELL) {
  // Full-dynamic lane: suffix -bwave / -bcut makes the building itself change every frame (building.ts).
  const buildingKind = /-b(wave|cut)$/.exec(sceneArg)?.[1] as 'wave' | 'cut' | undefined;
  const sceneName = buildingKind ? sceneArg.slice(0, -('-b'.length + buildingKind.length)) : sceneArg;
  let spec: SceneSpec;
  let upload: ImageUploader = async () => undefined;
  if (sceneName.startsWith('leak-')) spec = leakRoom(Number(sceneName.slice(5)));
  else if (sceneName.startsWith('town')) spec = townScene(sceneName);
  else {
    const s = await sponza();
    upload = s.upload;
    spec = sponzaScene(sceneName, parseGltf(s.json, s.bin));
  }
  if (buildingKind) spec = withBuildingMotion(spec, buildingKind);
  // Phase 32: every scene whose building does not cut (cut collapses triangles to a far vertex, which the clustered copies
  // do not follow) is a world: chunks and clustered copies for the voxel build (one instance unless widened).
  if (spec.building?.kind !== 'cut') {
    const st = spec.dynamic?.firstTriangle ?? spec.scene.triangleCount;
    const sv = spec.dynamic ? spec.dynamic.objects[0].firstVertex : spec.scene.positions.length / 3;
    const w = withWorld(spec.scene, triangleTable(spec.scene), st, sv, spec.instances ?? [[0, 0, 0]], DEFAULT_VOX.v0, DEFAULT_VOX.levels, lod0Cell);
    spec = { ...spec, scene: w.scene, world: w.world };
  } else if (spec.instances) throw new Error('-bcut is not supported on instanced worlds');
  return { spec, upload };
}
