const SSO_AUTHORIZE_URL = import.meta.env.VITE_SSO_AUTHORIZE_URL ?? ''
const SSO_CLIENT_ID = import.meta.env.VITE_SSO_CLIENT_ID ?? ''
const SSO_REDIRECT_URI =
  import.meta.env.VITE_SSO_REDIRECT_URI ?? `${window.location.origin}/auth/callback`

export function buildSsoAuthorizeUrl(): string {
  const params = new URLSearchParams({
    client_id: SSO_CLIENT_ID,
    redirect_uri: SSO_REDIRECT_URI,
    response_type: 'code',
    state: crypto.randomUUID(),
  })
  return `${SSO_AUTHORIZE_URL}?${params.toString()}`
}

export function redirectToSso() {
  window.location.href = buildSsoAuthorizeUrl()
}
