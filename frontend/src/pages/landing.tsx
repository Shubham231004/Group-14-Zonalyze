import { SignIn } from "@clerk/clerk-react";
import { MapPin, Wallet, Scale, MessageCircleQuestion, Trophy } from "lucide-react";

/**
 * BestSpot public landing — what a signed-out visitor sees.
 *
 * Design intent: a nervous first-time (or fifth-time) owner arrives full of
 * questions — "will it work? what will it cost? who's already there?" — and the
 * page answers them visually in seconds, then hands them the sign-in.
 * Editorial-cartography brand: warm paper, ink, the red pin.
 */

/* A hand-built map vignette — paper, streets, radius, pins, verdict. */
function MapVignette() {
  return (
    <div className="relative w-full aspect-[4/3] rounded-2xl border border-border bg-card overflow-hidden shadow-[0_24px_60px_-24px_rgba(33,29,26,0.25)]">
      {/* street grid */}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 300" aria-hidden>
        <g stroke="hsl(33 20% 88%)" strokeWidth="6" strokeLinecap="round">
          <path d="M0 80 H400" />
          <path d="M0 170 H400" />
          <path d="M0 245 H400" />
          <path d="M90 0 V300" />
          <path d="M210 0 V300" />
          <path d="M320 0 V300" />
        </g>
        <g stroke="hsl(33 20% 92%)" strokeWidth="3" strokeLinecap="round">
          <path d="M0 40 H400" />
          <path d="M0 125 H400" />
          <path d="M150 0 V300" />
          <path d="M265 0 V300" />
        </g>
        {/* park + water for warmth */}
        <rect x="222" y="182" width="86" height="52" rx="10" fill="hsl(140 30% 88%)" />
        <path d="M0 262 Q120 240 400 278 L400 300 L0 300 Z" fill="hsl(200 45% 90%)" />
        {/* the analysis radius */}
        <circle cx="176" cy="140" r="92" fill="hsl(4 71% 50% / 0.07)" stroke="hsl(4 71% 50% / 0.75)" strokeWidth="2.5" strokeDasharray="1 0" />
      </svg>

      {/* your spot */}
      <span className="brand-pin pin-drop absolute text-5xl" style={{ left: "41%", top: "40%" }} aria-hidden />
      {/* competitors */}
      {[
        { left: "28%", top: "26%" },
        { left: "55%", top: "31%" },
        { left: "33%", top: "58%" },
        { left: "60%", top: "55%" },
      ].map((pos, i) => (
        <span
          key={i}
          className="brand-pin absolute text-2xl opacity-55"
          style={{ ...pos, animation: `rise-in 0.5s ${0.55 + i * 0.12}s both` }}
          aria-hidden
        />
      ))}

      {/* verdict chip */}
      <div className="absolute right-4 top-4 rise-in rounded-xl border border-accent/30 bg-card px-3.5 py-2.5 shadow-md" style={{ animationDelay: "1.1s" }}>
        <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-semibold">Verdict</p>
        <p className="font-display text-accent text-lg font-semibold leading-tight">Worth it ✓</p>
        <p className="text-[10px] text-muted-foreground">4 competitors · demand strong</p>
      </div>

      {/* comparison chip */}
      <div className="absolute left-4 bottom-4 rise-in rounded-xl border border-border bg-card px-3.5 py-2.5 shadow-md" style={{ animationDelay: "1.3s" }}>
        <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-semibold">Best spots for a bakery</p>
        <div className="mt-1 space-y-0.5 text-[11px] font-mono">
          <p className="text-foreground">1. Waterloo <span className="text-accent font-semibold">82</span></p>
          <p className="text-muted-foreground">2. Kitchener 74</p>
          <p className="text-muted-foreground">3. Guelph 61</p>
        </div>
      </div>
    </div>
  );
}

const QUESTIONS = [
  {
    icon: MapPin,
    q: "Who's already there?",
    a: "Every competitor near your spot, pinned on a real map.",
  },
  {
    icon: Wallet,
    q: "What will it cost me?",
    a: "Rent, staff, and running costs — estimated in plain dollars.",
  },
  {
    icon: Scale,
    q: "Will it actually work?",
    a: "A straight verdict with a score, not a maybe.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* nav */}
      <header className="max-w-6xl mx-auto px-6 pt-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="brand-pin text-2xl" aria-hidden />
          <span className="font-display text-xl font-semibold">BestSpot</span>
        </div>
        <a
          href="#signin"
          className="text-sm font-semibold text-foreground border border-border rounded-full px-4 py-1.5 hover:border-primary hover:text-primary transition-colors"
        >
          Sign in
        </a>
      </header>

      {/* hero */}
      <main className="max-w-6xl mx-auto px-6">
        <section className="grid lg:grid-cols-2 gap-12 items-center pt-14 pb-10">
          <div className="space-y-7">
            <h1 className="rise-in font-display font-semibold text-5xl md:text-6xl leading-[1.04] tracking-tight">
              Find your best spot
              <span className="brand-pin pin-drop text-4xl md:text-5xl ml-2" aria-hidden />
              <br />
              <span className="text-muted-foreground">for your next business.</span>
            </h1>
            <p className="rise-in text-lg text-muted-foreground max-w-md leading-relaxed" style={{ animationDelay: "0.15s" }}>
              First café or fourth franchise — pick a spot on the map, name your idea,
              and get a straight answer{" "}
              <span className="text-foreground font-medium">before you sign a lease</span>.
            </p>

            {/* the questions in their head, answered */}
            <div className="rise-in space-y-3 pt-1" style={{ animationDelay: "0.3s" }}>
              {QUESTIONS.map(({ icon: Icon, q, a }) => (
                <div key={q} className="flex items-start gap-3.5">
                  <div className="mt-0.5 rounded-lg bg-primary/8 border border-primary/15 p-2">
                    <Icon className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <p className="font-display font-semibold text-[17px] leading-snug">{q}</p>
                    <p className="text-sm text-muted-foreground">{a}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rise-in" style={{ animationDelay: "0.25s" }}>
            <MapVignette />
            <p className="mt-3 text-center text-xs text-muted-foreground">
              Real map · real competitors · real census data — this is what your answer looks like.
            </p>
          </div>
        </section>

        {/* the best-spot promise */}
        <section className="py-10 border-t border-border">
          <div className="grid md:grid-cols-[auto_1fr] gap-6 items-center max-w-3xl mx-auto">
            <div className="rounded-2xl bg-primary/8 border border-primary/15 p-4 justify-self-center">
              <Trophy className="w-8 h-8 text-primary" />
            </div>
            <div>
              <h2 className="font-display text-2xl md:text-3xl font-semibold leading-snug">
                We don't just check one spot.
                <span className="text-primary"> We find your best one.</span>
              </h2>
              <p className="mt-2 text-muted-foreground text-sm md:text-base">
                BestSpot compares nearby cities and distances with the same numbers, ranks
                them, and tells you where your idea wins — with an assistant that answers
                your questions in plain language.
                <MessageCircleQuestion className="inline w-4 h-4 ml-1.5 -mt-0.5 text-primary" />
              </p>
            </div>
          </div>
        </section>

        {/* sign-in */}
        <section id="signin" className="py-12 border-t border-border">
          <div className="max-w-md mx-auto text-center space-y-6">
            <div>
              <h2 className="font-display text-3xl font-semibold">See your spot.</h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Free to try. Your first answer takes about a minute.
              </p>
            </div>
            <div className="flex justify-center">
              <SignIn routing="hash" />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border py-6">
        <p className="text-center text-xs text-muted-foreground">
          <span className="brand-pin text-sm mr-1.5" aria-hidden />
          BestSpot — find your best spot for your next business. Built on real map, census,
          and market data for Ontario.
        </p>
      </footer>
    </div>
  );
}
