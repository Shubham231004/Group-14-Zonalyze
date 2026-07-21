import { createRoot } from "react-dom/client";
import { ClerkProvider, SignedIn, SignedOut, SignIn } from "@clerk/clerk-react";
import App from "./App";
import "./index.css";
import { installAuthFetch } from "./lib/authFetch";

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined;

const root = createRoot(document.getElementById("root")!);

if (clerkKey) {
  // Auth ON: attach Clerk tokens to API calls and gate the app behind sign-in.
  installAuthFetch();
  root.render(
    <ClerkProvider publishableKey={clerkKey}>
      <SignedIn>
        <App />
      </SignedIn>
      <SignedOut>
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <SignIn routing="hash" />
        </div>
      </SignedOut>
    </ClerkProvider>,
  );
} else {
  // Auth OFF (no publishable key configured): render the app exactly as before.
  root.render(<App />);
}
