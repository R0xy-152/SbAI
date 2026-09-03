const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]'])

/** 公网登录页只能通过 HTTPS 提交邀请码；localhost HTTP 留给本地联调。 */
export function isInsecurePublicHttp(
  location: Pick<Location, 'protocol' | 'hostname'>,
): boolean {
  return location.protocol === 'http:' && !LOOPBACK_HOSTS.has(location.hostname)
}
