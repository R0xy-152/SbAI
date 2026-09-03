import { describe, expect, it } from 'vitest'
import { isInsecurePublicHttp } from '../transport-security'

describe('isInsecurePublicHttp', () => {
  it('阻止公网 IP 或域名通过 HTTP 提交邀请码', () => {
    expect(isInsecurePublicHttp({ protocol: 'http:', hostname: '114.55.133.96' })).toBe(true)
    expect(isInsecurePublicHttp({ protocol: 'http:', hostname: 'example.com' })).toBe(true)
  })

  it('允许 HTTPS 和 localhost 本地联调', () => {
    expect(isInsecurePublicHttp({ protocol: 'https:', hostname: 'sbai.xin' })).toBe(false)
    expect(isInsecurePublicHttp({ protocol: 'http:', hostname: 'localhost' })).toBe(false)
    expect(isInsecurePublicHttp({ protocol: 'http:', hostname: '127.0.0.1' })).toBe(false)
  })
})
