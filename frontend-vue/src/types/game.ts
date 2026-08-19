// GameView 运行时状态（docs/13 §10）：
// backend response 经 Adapter 归一为 PresentationState + interaction。
export interface GameViewState {
  sessionId: string
  presentation: import('./presentation').PresentationState
  interaction: {
    canInput: boolean
  }
}
