// happy-dom 不加载真实图片：RoleSprite 的 new Image() 需要同步完成 load，
// 否则角色头像路径解析一直挂起（docs/13 §26.1 测试桩，Fixture ≠ Production）。
export class FakeImage {
  onload: (() => void) | null = null
  onerror: ((e: unknown) => void) | null = null
  private _src = ''
  set src(v: string) {
    this._src = v
    queueMicrotask(() => this.onload?.())
  }
  get src() {
    return this._src
  }
  decode(): Promise<void> {
    return Promise.resolve()
  }
}