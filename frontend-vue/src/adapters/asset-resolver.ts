import { characterAssetUrl, type CharacterAssetKey } from '../api/assets'

// docs/13 §8.3 / §11.2：角色资源统一由 asset-resolver 输出 Web URL。
// 当前 repo 素材约定（docs/17 §6.2）：
//   deepseek → /char/deepseek/pic/deepseek_main.png（差分 8 表情已入库）
//   chatgpt  → /char/chatgpt/pic/chatgpt_main.png（差分 8 表情已入库）
//   claude   → /char/claude/pic/claude_main.png（差分 7 表情已入库）
//   doubao   → /char/doubao/pic/doubao_placeholder.svg（暂无正式立绘）
// 差分表情接线（docs/17 §6.3）：命名约定 {角色}_{emotion英文id}.png，
// neutral 一律用 main。前端不维护文件清单（补图不应触发改代码）→
// 编程式 Image 探测 + 模块级缓存；404/加载失败回落 main 单图
//（豆包补图后自动生效，无需改代码）。
const CHARACTER_MAIN_ASSET: Record<string, string> = {
  deepseek: '/char/deepseek/pic/deepseek_main.png',
  chatgpt: '/char/chatgpt/pic/chatgpt_main.png',
  claude: '/char/claude/pic/claude_main.png',
  doubao: '/char/doubao/pic/doubao_placeholder.svg',
}

/** (角色, 表情) → 解析结果 Promise：并发调用共享同一探测，成功后永久缓存 */
const probedDiff = new Map<string, Promise<string>>()

function assetExists(url: string): Promise<boolean> {
  // 用编程式 Image 而非 fetch HEAD：404 不会在浏览器控制台刷错误噪音；
  // 探测成功的图片进入 HTTP 缓存，后续立绘加载直接命中。
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve(true)
    img.onerror = () => resolve(false)
    img.src = url
  })
}

export async function resolveCharacterAsset(key: CharacterAssetKey): Promise<string> {
  const main = CHARACTER_MAIN_ASSET[key.characterId]
  if (!main) return characterAssetUrl(key)
  const emotion = key.emotion && key.emotion !== 'neutral' ? key.emotion : null
  if (!emotion) return main
  const cacheKey = `${key.characterId}:${emotion}`
  let pending = probedDiff.get(cacheKey)
  if (!pending) {
    pending = (async () => {
      const diff = `/char/${key.characterId}/pic/${key.characterId}_${emotion}.png`
      return (await assetExists(diff)) ? diff : main
    })()
    probedDiff.set(cacheKey, pending)
  }
  return pending
}
