// 该 happy-dom 版本不提供 window.localStorage（仅 sessionStorage），而多个
// store/视图 spec 直接引用裸 localStorage（与浏览器行为一致）。这里补一个
// 内存实现，测试之间由各 spec 的 beforeEach clear() 隔离。
class MemoryStorage implements Storage {
  private store = new Map<string, string>()

  get length(): number {
    return this.store.size
  }

  clear(): void {
    this.store.clear()
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null
  }

  removeItem(key: string): void {
    this.store.delete(key)
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value))
  }
}

const storage = new MemoryStorage()
if (typeof globalThis.localStorage === "undefined") {
  ;(globalThis as unknown as Record<string, unknown>).localStorage = storage
}
if (typeof window !== "undefined" && typeof window.localStorage === "undefined") {
  ;(window as unknown as Record<string, unknown>).localStorage = storage
}
