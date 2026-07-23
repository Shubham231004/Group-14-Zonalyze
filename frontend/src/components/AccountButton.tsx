import { UserButton } from "@clerk/clerk-react";

const clerkEnabled = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY);

/**
 * Clerk account menu — avatar opening "Manage account" / "Sign out".
 * Renders nothing when auth is disabled so the app still works keyless.
 */
export default function AccountButton() {
  if (!clerkEnabled) return null;
  return (
    <UserButton
      afterSignOutUrl="/"
      appearance={{ elements: { userButtonAvatarBox: { width: "2.1rem", height: "2.1rem" } } }}
    />
  );
}
