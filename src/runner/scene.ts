// Scene names of the runners -> SceneSpec. The platform supplies Sponza (glTF JSON, binary buffer, image uploader).
import { parseGltf } from '../core/gltf.ts';
import type { ImageUploader } from '../core/scene_gpu.ts';
import { leakRoom, sponzaScene, townScene, withBuildingMotion, type SceneSpec } from '../core/scenes.ts';

export async function loadScene(sceneArg: string, sponza: () => Promise<{ json: any; bin: ArrayBuffer; upload: ImageUploader }>) {
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
  return { spec, upload };
}
