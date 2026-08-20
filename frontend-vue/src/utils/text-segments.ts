// docs/16 P6：台词分段 —— 按换行切成非空段（trim 后过滤空行），逐段播放。
export function splitTextSegments(text: string): string[] {
  return text
    .split(String.fromCharCode(10))
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}
