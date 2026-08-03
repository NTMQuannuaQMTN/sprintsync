/**
 * Browser Supabase client — owns the entire GitHub OAuth flow and session.
 * The anon key is safe to expose client-side; Row Level Security on the
 * database (see apps/api/alembic/versions/001_initial_schema.py) is what
 * actually protects data, not secrecy of this key.
 */
import { createClient } from '@supabase/supabase-js'

const url = process.env.NEXT_PUBLIC_SUPABASE_URL
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!url || !anonKey) {
  // Warn, don't throw: this module is imported by client components that
  // Next.js prerenders at build time even without a browser, so throwing
  // here would fail `next build` itself whenever these aren't set — e.g.
  // in this repo's own sandbox, which has no real Supabase project wired
  // up yet. A placeholder client lets the build succeed; any real auth
  // attempt against a placeholder URL fails at the point of the actual
  // network call, with a clear cause, instead of crashing page generation.
  console.warn(
    'NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY are not set — see apps/web/.env.example. Auth will not work until they are.',
  )
}

export const supabase = createClient(
  url || 'https://placeholder.supabase.co',
  anonKey || 'placeholder-anon-key',
  {
    auth: {
      // Explicit, not the library default ('implicit'). PKCE is what
      // Supabase's own docs recommend for all new apps, and it's what the
      // hosted GitHub OAuth callback redirects with (?code=...) in
      // practice — leaving this on 'implicit' causes the client to detect
      // a flow-type mismatch on the redirect and silently discard the
      // session instead of exchanging the code, with no error surfaced.
      flowType: 'pkce',
    },
  },
)
