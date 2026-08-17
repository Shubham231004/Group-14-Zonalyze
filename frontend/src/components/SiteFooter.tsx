import BrandLogo from "@/components/BrandLogo";

const TEAM_MEMBERS = [
  "Girish Bhuteja",
  "Shubham Patel",
  "Kalp Mehta",
  "Jainish Prajapati",
];

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <BrandLogo size="compact" />
        <div className="site-footer-credits">
          <p>Designed and built by</p>
          <ul aria-label="BestSpot project team">
            {TEAM_MEMBERS.map((member) => <li key={member}>{member}</li>)}
          </ul>
        </div>
      </div>
    </footer>
  );
}
