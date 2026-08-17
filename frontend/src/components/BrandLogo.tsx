type BrandLogoProps = {
  className?: string;
  href?: string;
  size?: "compact" | "default" | "large";
};

const LOGO_ALT = "BestSpot.biz — Big ideas deserve the right place.";

export default function BrandLogo({
  className = "",
  href,
  size = "default",
}: BrandLogoProps) {
  const logo = (
    <span className={`brand-logo brand-logo--${size} ${className}`.trim()}>
      <img
        className="brand-logo__image"
        src="/branding/bestspot-logo.png"
        alt={href ? "" : LOGO_ALT}
      />
    </span>
  );

  if (!href) return logo;

  return (
    <a className="brand-logo-link" href={href} aria-label="BestSpot home">
      {logo}
    </a>
  );
}
