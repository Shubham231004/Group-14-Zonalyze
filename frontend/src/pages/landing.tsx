import { SignIn } from "@clerk/clerk-react";
import {
  ArrowRight,
  BarChart3,
  Bot,
  Building2,
  Check,
  CircleDollarSign,
  Map,
  MapPin,
  Scale,
  Search,
  ShieldCheck,
  Sparkles,
  Store,
  Users,
} from "lucide-react";
import BrandLogo from "@/components/BrandLogo";
import SiteFooter from "@/components/SiteFooter";

function ProductMapPreview() {
  const competitors = [
    { name: "Daily Bread", left: "24%", top: "27%" },
    { name: "Crumb & Co.", left: "71%", top: "24%" },
    { name: "Baker Street", left: "63%", top: "66%" },
    { name: "Morning Loaf", left: "29%", top: "71%" },
  ];

  return (
    <div className="map-preview-shell" aria-label="Example BestSpot competition map for a bakery">
      <div className="map-preview-toolbar">
        <div><p className="eyebrow">Live decision preview</p><p className="mt-1 text-sm font-semibold text-foreground">Independent bakery · Waterloo</p></div>
        <span className="status-chip"><span className="status-dot" />Real map view</span>
      </div>
      <div className="map-preview-canvas">
        <div className="map-road map-road-a" /><div className="map-road map-road-b" /><div className="map-road map-road-c" /><div className="map-road map-road-d" />
        <div className="map-park"><span>Victoria Park</span></div>
        <div className="map-building building-a" /><div className="map-building building-b" /><div className="map-building building-c" /><div className="map-catchment" />
        {competitors.map((competitor) => (
          <div key={competitor.name} className="map-competitor" style={{ left: competitor.left, top: competitor.top }} title={competitor.name}><Store className="h-3.5 w-3.5" /></div>
        ))}
        <div className="map-hero-pin" aria-label="Recommended area"><MapPin className="h-7 w-7 fill-primary text-primary" /><span>Best area</span></div>
        <div className="map-score-card">
          <div className="score-orbit"><strong>82</strong><span>/100</span></div>
          <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-accent">Strong fit</p><p className="mt-0.5 text-[11px] text-muted-foreground">Demand beats competition</p></div>
        </div>
        <div className="map-legend-card"><span><i className="legend-pin" /> Your best area</span><span><i className="legend-store" /> 4 competitors</span></div>
      </div>
    </div>
  );
}

const QUESTIONS = [
  { icon: MapPin, question: "Who is already nearby?", answer: "See competitors around the exact address, not just a city average." },
  { icon: Users, question: "Are my customers there?", answer: "Understand the people, activity, and demand inside your catchment." },
  { icon: CircleDollarSign, question: "What could it cost?", answer: "Plan with local lease and operating ranges before committing." },
  { icon: Scale, question: "Is this my best option?", answer: "Compare cities and radiuses with the same decision score." },
];

const STEPS = [
  { number: "01", icon: Search, title: "Describe the idea", copy: "Choose any Ontario city, address, business type, and customer radius." },
  { number: "02", icon: Map, title: "See the market", copy: "BestSpot maps competitors and reads demand, population, and cost evidence." },
  { number: "03", icon: BarChart3, title: "Choose with confidence", copy: "Get a clear score, trade-offs, and a ranked comparison of other spots." },
];

export default function Landing() {
  return (
    <div id="top" className="min-h-screen bg-background text-foreground">
      <header className="landing-nav">
        <BrandLogo href="#top" size="compact" />
        <nav className="hidden items-center gap-7 md:flex" aria-label="Main navigation">
          <a href="#answers" className="nav-link">What you learn</a><a href="#how-it-works" className="nav-link">How it works</a><a href="#compare" className="nav-link">Compare spots</a>
        </nav>
        <a href="#signin" className="button-secondary">Sign in<ArrowRight className="h-3.5 w-3.5" /></a>
      </header>
      <main>
        <section className="landing-hero page-shell">
          <div className="hero-copy">
            <div className="trust-kicker rise-in"><ShieldCheck className="h-4 w-4" />Location decisions for Ontario business owners</div>
            <h1 className="rise-in hero-title" style={{ animationDelay: "80ms" }}>Find the best spot<span className="hero-pin-word"><span className="brand-pin pin-drop" aria-hidden /></span><span>for your next business.</span></h1>
            <p className="rise-in hero-description" style={{ animationDelay: "150ms" }}>Before you sign a lease, see the competition, understand the costs, and compare where your idea has the strongest chance to work.</p>
            <div className="rise-in flex flex-wrap gap-3" style={{ animationDelay: "220ms" }}><a href="#signin" className="button-primary">Check a location<ArrowRight className="h-4 w-4" /></a><a href="#how-it-works" className="button-quiet">See how it works</a></div>
            <div className="rise-in hero-proof" style={{ animationDelay: "280ms" }}><span><Check className="h-3.5 w-3.5" /> Takes about a minute</span><span><Check className="h-3.5 w-3.5" /> Real market evidence</span><span><Check className="h-3.5 w-3.5" /> Plain-language answers</span></div>
          </div>
          <div className="rise-in hero-visual" style={{ animationDelay: "180ms" }}>
            <div className="visual-orbit visual-orbit-one" /><div className="visual-orbit visual-orbit-two" /><ProductMapPreview />
            <div className="floating-note floating-note-top"><Building2 className="h-4 w-4 text-primary" /><span><strong>4</strong> nearby competitors</span></div>
            <div className="floating-note floating-note-bottom"><Sparkles className="h-4 w-4 text-accent" /><span>Better than <strong>2 nearby cities</strong></span></div>
          </div>
        </section>
        <section className="proof-bar" aria-label="Data sources"><div className="page-shell proof-bar-inner"><p>One decision view, built from:</p><span>Competition</span><span>Local demand</span><span>Population</span><span>Lease ranges</span><span>Transit & activity</span></div></section>
        <section id="answers" className="page-shell section-space">
          <div className="section-heading"><p className="eyebrow">The questions already on your mind</p><h2>You bring the idea. BestSpot brings the clarity.</h2><p>No jargon-heavy report to decode. Start with the answers that affect your decision.</p></div>
          <div className="question-grid">{QUESTIONS.map(({ icon: Icon, question, answer }) => (<article key={question} className="question-card"><div className="icon-tile"><Icon className="h-5 w-5" /></div><h3>{question}</h3><p>{answer}</p></article>))}</div>
        </section>
        <section id="how-it-works" className="process-section"><div className="page-shell section-space">
          <div className="section-heading section-heading-left"><p className="eyebrow">From doubt to a decision</p><h2>See the answer take shape.</h2></div>
          <div className="process-track">{STEPS.map(({ number, icon: Icon, title, copy }, index) => (<article key={number} className="process-step"><div className="process-number">{number}</div><div className="process-icon"><Icon className="h-5 w-5" /></div><h3>{title}</h3><p>{copy}</p>{index < STEPS.length - 1 && <ArrowRight className="process-arrow h-5 w-5" />}</article>))}</div>
        </div></section>
        <section id="compare" className="page-shell section-space comparison-feature">
          <div className="comparison-copy"><p className="eyebrow">The feature that changes the decision</p><h2>Do not settle for a good spot. Find the best one.</h2><p>Save each location you are considering and compare feasibility, costs, demand, competition, and confidence side by side. The same idea can tell a very different story a few kilometres away.</p><ul className="feature-checks"><li><Check /> Ranked with one consistent score</li><li><Check /> Trade-offs shown in plain language</li><li><Check /> Revisit saved searches at any time</li></ul></div>
          <div className="ranking-card" aria-label="Example city comparison"><div className="ranking-header"><div><p className="eyebrow">Bakery comparison</p><h3>Three places. One clear leader.</h3></div><Scale className="h-6 w-6 text-primary" /></div>
            {[{ rank: 1, city: "Waterloo", score: 82, note: "Best overall balance", best: true }, { rank: 2, city: "Kitchener", score: 74, note: "Higher demand, higher cost" }, { rank: 3, city: "Guelph", score: 68, note: "Lower competition, smaller reach" }].map((row) => (
              <div key={row.city} className={`ranking-row ${row.best ? "ranking-row-best" : ""}`}><span className="rank-number">{row.rank}</span><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><strong>{row.city}</strong>{row.best && <span className="best-badge">Best spot</span>}</div><p>{row.note}</p></div><div className="rank-score"><strong>{row.score}</strong><span>/100</span></div></div>
            ))}
          </div>
        </section>
        <section className="assistant-strip"><div className="page-shell assistant-strip-inner"><div className="assistant-icon"><Bot className="h-6 w-6" /></div><div><p className="eyebrow">Questions do not stop after the score</p><h2>Ask BestSpot anything about your result.</h2></div><p>“Why is the competition score high?” “What happens at a 3 km radius?” Your assistant answers from the active location and its evidence.</p></div></section>
        <section id="signin" className="page-shell sign-in-section"><div className="sign-in-copy"><BrandLogo href="#top" size="large" /><p className="eyebrow mt-10">Your next location deserves a real answer</p><h2>Start with one spot.</h2><p>Sign in to keep your searches private, save promising locations, and compare them when you are ready.</p><div className="sign-in-trust"><ShieldCheck className="h-5 w-5" /><span>Secure sign-in. We never ask for banking or lease documents.</span></div></div><div className="sign-in-card"><SignIn routing="hash" /></div></section>
      </main>
      <SiteFooter />
    </div>
  );
}
