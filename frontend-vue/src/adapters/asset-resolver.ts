import { characterAssetUrl, type CharacterAssetKey } from '../api/assets'

// docs/13 §8.3 / §11.2：角色资源统一由 asset-resolver 输出 Web URL。
// 后续若引入差分表情（spriteKey + emotion），在本层扩展，不让组件感知资源细节。
export function resolveCharacterAsset(key: CharacterAssetKey): string {
  return characterAssetUrl(key)
}
