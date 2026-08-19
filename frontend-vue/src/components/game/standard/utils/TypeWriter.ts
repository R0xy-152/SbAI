// Adapted from LingChat (AGPL-3.0): src/utils/typewriter/TypeWriter.ts
// Modification: removed all AudioContext / sound-effect logic (docs/13 §11:
// 无关音频控制删除), so this is a pure character-by-character typing engine.
export type TypeWriterStatus = 'idle' | 'typing' | 'completed'

export class TypeWriter {
  private element: HTMLElement
  private timer: ReturnType<typeof setTimeout> | null = null
  private speed: number
  private generation: number
  private textBuffer: string
  private writeFn: ((element: HTMLElement, text: string) => void) | null

  private onFinishCallback: (() => void) | null
  private onTextUpdateCallback: ((text: string) => void) | null

  // State
  private _status: TypeWriterStatus = 'idle'

  constructor(
    element: HTMLElement,
    onTextUpdateCallback?: (text: string) => void,
    _soundUrls?: string[],
    writeFn?: (element: HTMLElement, text: string) => void,
  ) {
    this.element = element
    this.timer = null
    this.speed = 50
    this.generation = 0
    this.textBuffer = ''
    this.writeFn = writeFn || null
    this.onFinishCallback = null
    this.onTextUpdateCallback = onTextUpdateCallback || null
  }

  /** Current typewriter state, queryable externally at any time. */
  public get status(): TypeWriterStatus {
    return this._status
  }

  // ─── Core Typing ─────────────────────────────────────────

  /**
   * Start typing the given text character by character.
   *
   * Returns a Promise that resolves when:
   *   - All characters have been displayed (natural completion), OR
   *   - The animation is cancelled by a subsequent `start()` call
   *
   * Safe to call while a previous animation is still running — the old one
   * is cancelled cleanly via generation counter before the new one begins.
   */
  public start(text: string, speed?: number): Promise<void> {
    // Cancel any previous animation and advance generation
    this.stop()
    this.generation++
    const currentGen = this.generation

    this._status = 'typing'
    this.textBuffer = ''

    // Parse speed
    if (speed !== undefined) {
      this.speed = Number.isInteger(speed) ? speed : parseInt(String(speed), 10) || 50
    }

    let i = 0

    return new Promise<void>((resolve) => {
      const typing = (): void => {
        // Guard: stale generation means a newer start() has taken over
        if (this.generation !== currentGen) {
          resolve()
          return
        }

        if (i < text.length) {
          this.textBuffer += text.charAt(i)
          if (this.writeFn) {
            this.writeFn(this.element, this.textBuffer)
          } else if (
            this.element instanceof HTMLInputElement ||
            this.element instanceof HTMLTextAreaElement
          ) {
            this.element.value = this.textBuffer
          }
          if (this.onTextUpdateCallback) {
            this.onTextUpdateCallback(this.textBuffer)
          }
          i++
          this.element.scrollTop = this.element.scrollHeight

          //timer接收delay的是延迟（越大越慢），而传入的speed是速度（越大越快）
          const maxDelay = 200
          const minDelay = 10
          const randomVariation = this.speed * 0.2
          const delay =
            maxDelay -
            ((this.speed - 1) / 99) * (maxDelay - minDelay) +
            Math.random() * randomVariation

          this.timer = setTimeout(typing, delay)
        } else {
          this.finish()
          resolve()
        }
      }

      // Start the typing loop immediately
      typing()
    })
  }

  /** Immediately complete the current typing animation (show all text). */
  public finish(): void {
    this.stopTimer()
    this._status = 'completed'
    this.element.style.setProperty('border-right', 'none')
    if (this.onFinishCallback) {
      this.onFinishCallback()
    }
  }

  /**
   * Cancel the current typing animation.
   * Resets status to idle but does NOT clear the displayed text.
   */
  public stop(): void {
    this.stopTimer()
    this.generation++ // invalidate any lingering typing closures
    this._status = 'idle'
  }

  /** Clear the DOM element and internal text buffer. */
  public clear(): void {
    if (this.writeFn) {
      this.writeFn(this.element, '')
    } else if (
      this.element instanceof HTMLInputElement ||
      this.element instanceof HTMLTextAreaElement
    ) {
      this.element.value = ''
    }
    this.textBuffer = ''
  }

  /** Full cleanup: stop animation and clear text. */
  public destroy(): void {
    this.stop()
    this.clear()
  }

  // ─── Callback registration ───────────────────────────────

  public onFinish(callback: () => void): void {
    this.onFinishCallback = callback
  }

  // ─── Private helpers ─────────────────────────────────────

  private stopTimer(): void {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
  }
}
