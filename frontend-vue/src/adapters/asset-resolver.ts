import { characterAssetUrl, type CharacterAssetKey } from '../api/assets'

// docs/13 §8.3 / §11.2：角色资源统一由 asset-resolver 输出 Web URL。
// 当前 repo 素材约定：
//   deepseek → /char/deepseek/pic/deepseek_main.png
//   chatgpt  → /char/chatgpt/pic/chatgpt_main.png（2026-08-19 正式立绘）
//   claude   → /frontend-deprecated/public/characters/claude-main.png
//   doubao   → placeholder SVG（暂无正式立绘）
// 差分表情（emotion 专属立绘）当前无素材，单图 + 前端滤镜；后续若引入
// spriteKey + emotion 差分，在本层扩展，不让组件感知资源细节。
const CHARACTER_EMOTION_ASSET: Record<string, string> = {
  deepseek: '/char/deepseek/pic/deepseek_main.png',
  chatgpt: '/char/chatgpt/pic/chatgpt_main.png',
  claude: '/frontend-deprecated/public/characters/claude-main.png',
  doubao: '/frontend-deprecated/public/characters/claude-placeholder.svg',
}

export function resolveCharacterAsset(key: CharacterAssetKey): string {
  const fallback = CHARACTER_EMOTION_ASSET[key.characterId] ?? characterAssetUrl(key)
  return fallback
}
