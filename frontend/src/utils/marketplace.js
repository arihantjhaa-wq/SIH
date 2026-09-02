export const CATEGORY_OPTIONS = [
  "Grains",
  "Vegetables",
  "Fruits",
  "Oils",
  "Spices",
  "Dairy",
  "Nuts",
  "Pulses",
  "Sweeteners",
  "Herbs",
  "Other",
];

export const UNIT_OPTIONS = ["kg", "g", "litre", "ml", "dozen", "piece"];

export const MAX_SAVER_THRESHOLD = 35;

export function discountPct(p) {
  return Math.round(((p.indivPrice - p.bizPrice) / p.indivPrice) * 100);
}

export function isGstinValid(g) {
  return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(
    g.trim().toUpperCase(),
  );
}

export const money = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

export function photoUrl(product, w = 480, h = 360) {
  const seed = encodeURIComponent(product.photo || product.id);
  return `https://picsum.photos/seed/${seed}/${w}/${h}`;
}
