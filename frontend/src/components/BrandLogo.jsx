import React from "react";
import { Link } from "react-router-dom";
import { Leaf } from "lucide-react";

/**
 * कृषि Setu — reusable branded logo lockup (Gotu display typeface).
 *
 * The leaf mark lives INSIDE the `.brand-logo` flex capsule, so it inherits
 * the lockup's currentColor (warm gold on dark, forest ink on light) and
 * scales with the fluid clamp() font size via the `em`-based icon sizing in
 * index.css.
 *
 * Props:
 *   - to:       Route path — when provided the lockup becomes a <Link>
 *   - size:     "sm" | "md" | "lg" — default "md"
 *   - dark:     Boolean — true for LIGHT backgrounds (deep green ink variant)
 *   - className: Additional classes for the outer wrapper
 */
export default function BrandLogo({ to, size = "md", dark = false, className = "" }) {
  const sizeClass =
    size === "sm" ? "brand-logo--sm" : size === "lg" ? "brand-logo--lg" : "";

  const inner = (
    <span
      className={`brand-logo whitespace-nowrap${dark ? " brand-logo--light" : ""}${sizeClass ? ` ${sizeClass}` : ""}`}
      data-size={size}
    >
      <Leaf className="brand-logo-icon" strokeWidth={1.6} aria-hidden="true" />
      <span className="devanagari">कृषि</span>
      <span className="latin">Setu</span>
    </span>
  );

  const wrapperClasses = ["inline-flex items-center", className]
    .filter(Boolean)
    .join(" ");

  if (to) {
    return (
      <Link
        to={to}
        className={`${wrapperClasses} rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E5A93C]/60`}
        aria-label="कृषि Setu — home"
      >
        {inner}
      </Link>
    );
  }

  return <div className={wrapperClasses}>{inner}</div>;
}