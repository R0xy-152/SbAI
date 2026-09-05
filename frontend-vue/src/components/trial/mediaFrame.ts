// 试玩版：开场视频「冻结帧」共享缓存（docs/27 §7.1）。
// 开场视频在 TrialSceneSnapshot 播放时周期性把当前帧捕获为 dataURL 存入此模块；
// 进入碎裂（ShatterPuzzle）时读取它，作为四片玻璃共用的冻结源——避免四片各自挂一个不同步的视频。
let frame: string | null = null

export function getFrozenFrame(): string | null {
  return frame
}

export function setFrozenFrame(f: string | null): void {
  frame = f
}
