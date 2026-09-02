function seededRandom(seedStr) {
  let h = 1779033703 ^ seedStr.length;
  for (let i = 0; i < seedStr.length; i++) {
    h = Math.imul(h ^ seedStr.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function () {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
}

const REVIEW_NAMES = [
  "Anjali M.", "Rohan D.", "Priya S.", "Karan V.", "Meera J.",
  "Arjun K.", "Sneha R.", "Vikram T.", "Divya N.", "Sameer P.",
  "Ritu B.", "Faisal A.",
];

const REVIEW_TEMPLATES = [
  "Really fresh — arrived in great condition and tasted like it came straight from the farm.",
  "Good quality for the price. Will order again for the household.",
  "Packaging was solid and the {unit} weight was spot on.",
  "This is now our regular order. Consistent quality every time.",
  "Nice quality overall, though delivery took a little longer than expected.",
  "Better than what I usually get at the local market. Happy with this.",
  "Great value when buying in bulk for the shop.",
  "Tasted fresh and the farmer details on the listing gave me confidence.",
  "Solid everyday pick — nothing fancy, just reliably good.",
  "Would recommend to anyone looking for farm-direct produce.",
];

export function generateDescription(product) {
  const rnd = seededRandom(product.id + product.name);
  const notes = ["sun-ripened", "hand-picked", "carefully sorted", "harvest-fresh", "traditionally grown", "small-batch"];
  const uses = ["everyday cooking", "festive meals", "your kitchen staples", "bulk meal prep", "gifting and home use"];
  const note = notes[Math.floor(rnd() * notes.length)];
  const use = uses[Math.floor(rnd() * uses.length)];
  const money = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;
  return `${note[0].toUpperCase()}${note.slice(1)} ${product.name.toLowerCase()} sourced directly from ${product.farmer}, grown in the ${product.category.toLowerCase()} belt of their region. Sold by the ${product.unit}, it's a favorite for ${use}. Buying direct means the farmer earns a fairer share and you skip the middlemen markup — households pay ${money(product.indivPrice)}/${product.unit}, while verified businesses ordering at least ${product.minBulkQty} ${product.unit} unlock the bulk rate of ${money(product.bizPrice)}/${product.unit}.`;
}

export function generateReviews(product) {
  const rnd = seededRandom("rev-" + product.id);
  const count = 3 + Math.floor(rnd() * 4);
  const reviews = [];
  const usedNames = new Set();
  for (let i = 0; i < count; i++) {
    let name = REVIEW_NAMES[Math.floor(rnd() * REVIEW_NAMES.length)];
    while (usedNames.has(name) && usedNames.size < REVIEW_NAMES.length) {
      name = REVIEW_NAMES[Math.floor(rnd() * REVIEW_NAMES.length)];
    }
    usedNames.add(name);
    const rating = Math.min(5, 3 + Math.round(rnd() * 2));
    const template = REVIEW_TEMPLATES[Math.floor(rnd() * REVIEW_TEMPLATES.length)];
    const daysAgo = 2 + Math.floor(rnd() * 85);
    reviews.push({
      id: `${product.id}-r${i}`,
      name,
      rating,
      text: template.replace("{unit}", product.unit),
      daysAgo,
    });
  }
  return reviews.sort((a, b) => a.daysAgo - b.daysAgo);
}

export function avgRating(reviews) {
  if (!reviews.length) return 0;
  return reviews.reduce((s, r) => s + r.rating, 0) / reviews.length;
}

export function timeAgo(days) {
  if (days < 1) return "today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  const months = Math.round(days / 30);
  return months === 1 ? "1 month ago" : `${months} months ago`;
}
