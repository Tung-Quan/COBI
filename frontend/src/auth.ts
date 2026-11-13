import { createAuthClient } from '@neon/auth'
import { BetterAuthReactAdapter } from '@neon/auth/react/adapters'

const authUrl = import.meta.env.VITE_NEON_AUTH_URL?.trim() ?? ''
export const authEnabled = authUrl.length > 0

export const authClient = createAuthClient(authUrl || 'http://localhost:9999/auth', {
  adapter: BetterAuthReactAdapter(),
})

export async function getAuthToken(): Promise<string | null> {
  if (!authEnabled) return null
  // Neon Auth's Better Auth client adds the /token endpoint at runtime, but
  // @neon/auth 0.8.2 currently omits that endpoint from its exported client type.
  const clientWithJwtEndpoint = authClient as typeof authClient & {
    getToken: () => Promise<{ data?: { token: string } | null; error?: { message?: string } | null }>
  }
  const { data, error } = await clientWithJwtEndpoint.getToken()
  if (error) throw new Error('Your session expired. Sign in again to continue.')
  return data?.token ?? null
}
