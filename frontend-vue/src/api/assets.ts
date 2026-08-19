// 角色资源解析（docs/13 §8.3）：character_id + emotion → HTTP/static asset URL。
// 前端不访问宿主机绝对路径；不用 convertFileSrc / invoke。
// 现有仓库角色图位于 frontend-deprecated/public/characters/，命名规则在 Task 2 接入
// asset-resolver 时核对，此处为骨架占位。
const ASSET_BASE = '/frontend-deprecated/public/characters/'

export interface CharacterAssetKey {
  characterId: string
  emotion: string
}

export function characterAssetUrl({ characterId, emotion }: CharacterAssetKey): string {
  return `${ASSET_BASE}${characterId}/${emotion}.png`
}
