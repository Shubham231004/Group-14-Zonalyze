import { createRoot } from "react-dom/client";
import { ClerkProvider, SignedIn, SignedOut } from "@clerk/clerk-react";
import App from "./App";
import Landing from "./pages/landing";
import "./index.css";
import { installAuthFetch } from "./lib/authFetch";

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined;

const root = createRoot(document.getElementById("root")!);

if (clerkKey) {
  // Auth ON: attach Clerk tokens to API calls and gate the app behind sign-in.
  // Signed-out visitors get the BestSpot landing page (sign-in embedded) so they
  // understand the product before being asked for an account.
  installAuthFetch();
  root.render(
    <ClerkProvider
      publishableKey={clerkKey}
      appearance={{
        variables: {
          colorPrimary: "#d63a2c",
          fontFamily: '"Public Sans", system-ui, sans-serif',
          borderRadius: "0.75rem",
        },
      }}
    >
      <SignedIn>
        <App />
      </SignedIn>
      <SignedOut>
        <Landing />
      </SignedOut>
    </ClerkProvider>,
  );
} else {
  // Auth OFF (no publishable key configured): render the app exactly as before.
  root.render(<App />);
}
