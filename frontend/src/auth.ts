import { createAuthClient } from '@neon/auth'
import { BetterAuthReactAdapter } from '@neon/auth/react/adapters'

const authUrl = import.meta.env.VITE_NEON_AUTH_URL?.trim() ?? ''
export const authEnabled = authUrl.length > 0

export const authClient = createAuthClient(authUrl || 'http://localhost:9999/auth', {
  adapter: BetterAuthReactAdapter(),
})

export async function getAuthToken(): Promise<string | null> {
  if (!authEnabled) return null
  // Neon Auth's browser session API and its JWT endpoint use different paths.
  // The Better Auth client maps getToken() to /get-token, which Neon Auth does
  // not serve; fetch the documented /token endpoint with the session cookie.
  const response = await fetch(`${authUrl.replace(/\/+$/, '')}/token`, {
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(response.status === 401
      ? 'Your session is invalid or has expired.'
      : `Neon Auth could not provide a session token (${response.status}).`)
  }
  const payload: { token?: unknown } = await response.json()
  if (typeof payload.token !== 'string' || !payload.token) {
    throw new Error('Neon Auth returned an invalid session token.')
  }
  return payload.token
}
