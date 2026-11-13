import { createInternalNeonAuth } from '@neon/auth'
import { BetterAuthReactAdapter } from '@neon/auth/react/adapters'

const authUrl = import.meta.env.VITE_NEON_AUTH_URL?.trim() ?? ''
export const authEnabled = authUrl.length > 0

const neonAuth = createInternalNeonAuth(authUrl || 'http://localhost:9999/auth', {
  adapter: BetterAuthReactAdapter(),
})
export const authClient = neonAuth.adapter

export async function getAuthToken(): Promise<string | null> {
  if (!authEnabled) return null
  // The adapter helper reads Neon Auth's JWT-injected session; the Better Auth
  // client's getToken route maps to /get-token, which Neon Auth does not serve.
  return neonAuth.getJWTToken()
}
