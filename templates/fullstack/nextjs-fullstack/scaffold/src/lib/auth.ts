import NextAuth from "next-auth";
import type { NextAuthConfig } from "next-auth";

/**
 * NextAuth.js v5 configuration.
 *
 * This module configures authentication providers, session strategy,
 * and callbacks. Export the handlers for the API route and the auth()
 * function for use in server components and middleware.
 */

const config: NextAuthConfig = {
  // Configure authentication providers here.
  // Example: GitHub OAuth, Google, Credentials, etc.
  providers: [
    // Add your providers here. Example:
    // GitHub({
    //   clientId: process.env.GITHUB_CLIENT_ID!,
    //   clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    // }),
  ],

  // Session strategy: "jwt" (default) or "database"
  session: {
    strategy: "jwt",
  },

  // Custom pages (optional)
  pages: {
    signIn: "/auth/signin",
  },

  callbacks: {
    // Add user ID to the session
    session({ session, token }) {
      if (token.sub) {
        session.user.id = token.sub;
      }
      return session;
    },

    // Control who can sign in
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isProtected = nextUrl.pathname.startsWith("/dashboard");
      if (isProtected && !isLoggedIn) {
        return false; // Redirect to sign-in
      }
      return true;
    },
  },
};

export const { handlers, auth, signIn, signOut } = NextAuth(config);
