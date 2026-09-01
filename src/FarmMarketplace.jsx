import React, { useState, useMemo, useEffect } from "react";
import {
  Leaf,
  ShoppingCart,
  Building2,
  User,
  BadgePercent,
  Lock,
  Plus,
  Minus,
  Trash2,
  CheckCircle2,
  Truck,
  X,
  Sprout,
  Store,
  ArrowLeft,
  PackagePlus,
  ImageOff,
  Camera,
  Star,
  MessageSquare,
  MapPin,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Persistent state — same API as useState, but reads/writes localStorage
// so the value survives a page reload.
// ---------------------------------------------------------------------------

function usePersistentState(key, initialValue) {
  const [state, setState] = useState(() => {
    try {
      const saved = localStorage.getItem(key);
      return saved !== null ? JSON.parse(saved) : initialValue;
    } catch {
      return initialValue;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(state));
    } catch {
      // ignore quota / serialization errors
    }
  }, [key, state]);

  return [state, setState];
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

const PRODUCTS = [
  {
    id: "p1",
    name: "Sona Masoori Rice",
    category: "Grains",
    unit: "kg",
    photo: "rice grain",
    indivPrice: 62,
    bizPrice: 42,
    minBulkQty: 50,
    farmer: "Ravi Kumar, Nalgonda",
  },
  {
    id: "p2",
    name: "Vine-Ripened Tomatoes",
    category: "Vegetables",
    unit: "kg",
    photo: "tomatoes fresh",
    indivPrice: 38,
    bizPrice: 24,
    minBulkQty: 40,
    farmer: "Sunita Devi, Nashik",
  },
  {
    id: "p3",
    name: "Red Onions",
    category: "Vegetables",
    unit: "kg",
    photo: "red onions",
    indivPrice: 30,
    bizPrice: 19,
    minBulkQty: 60,
    farmer: "Prakash Patil, Nashik",
  },
  {
    id: "p4",
    name: "Cold-Pressed Mustard Oil",
    category: "Oils",
    unit: "litre",
    photo: "mustard oil bottle",
    indivPrice: 210,
    bizPrice: 165,
    minBulkQty: 20,
    farmer: "Harpreet Singh, Bathinda",
  },
  {
    id: "p5",
    name: "Turmeric (Whole)",
    category: "Spices",
    unit: "kg",
    photo: "turmeric root",
    indivPrice: 180,
    bizPrice: 110,
    minBulkQty: 25,
    farmer: "Lakshmi Reddy, Erode",
  },
  {
    id: "p6",
    name: "Wheat Atta",
    category: "Grains",
    unit: "kg",
    photo: "wheat flour",
    indivPrice: 48,
    bizPrice: 34,
    minBulkQty: 50,
    farmer: "Bhupinder Sidhu, Ludhiana",
  },
  {
    id: "p7",
    name: "Alphonso Mangoes",
    category: "Fruits",
    unit: "dozen",
    photo: "mango fruit",
    indivPrice: 650,
    bizPrice: 480,
    minBulkQty: 10,
    farmer: "Devendra More, Ratnagiri",
  },
  {
    id: "p8",
    name: "Jaggery Blocks",
    category: "Sweeteners",
    unit: "kg",
    photo: "jaggery",
    indivPrice: 70,
    bizPrice: 41,
    minBulkQty: 30,
    farmer: "Meena Yadav, Muzaffarnagar",
  },
  {
    id: "p9",
    name: "Potatoes",
    category: "Vegetables",
    unit: "kg",
    photo: "potatoes",
    indivPrice: 26,
    bizPrice: 17,
    minBulkQty: 75,
    farmer: "Gurmeet Kaur, Jalandhar",
  },
  {
    id: "p10",
    name: "Kashmiri Saffron",
    category: "Spices",
    unit: "g",
    photo: "saffron spice",
    indivPrice: 450,
    bizPrice: 300,
    minBulkQty: 200,
    farmer: "Abdul Rashid, Pampore",
  },
  {
    id: "p11",
    name: "A2 Desi Cow Ghee",
    category: "Dairy",
    unit: "kg",
    photo: "ghee butter",
    indivPrice: 950,
    bizPrice: 620,
    minBulkQty: 20,
    farmer: "Kishorbhai Patel, Anand",
  },
  {
    id: "p12",
    name: "Raw Forest Honey",
    category: "Sweeteners",
    unit: "kg",
    photo: "honey jar",
    indivPrice: 520,
    bizPrice: 310,
    minBulkQty: 30,
    farmer: "Bimal Mondal, Sundarbans",
  },
  {
    id: "p13",
    name: "Whole Cashews",
    category: "Nuts",
    unit: "kg",
    photo: "cashew nuts",
    indivPrice: 900,
    bizPrice: 640,
    minBulkQty: 25,
    farmer: "Vinayak Sawant, Sindhudurg",
  },
  {
    id: "p14",
    name: "Green Cardamom",
    category: "Spices",
    unit: "kg",
    photo: "cardamom spice",
    indivPrice: 2200,
    bizPrice: 1450,
    minBulkQty: 10,
    farmer: "Thomas Kurian, Idukki",
  },
  {
    id: "p15",
    name: "Malabar Black Pepper",
    category: "Spices",
    unit: "kg",
    photo: "black pepper spice",
    indivPrice: 650,
    bizPrice: 400,
    minBulkQty: 20,
    farmer: "Joseph Mathew, Wayanad",
  },
  {
    id: "p16",
    name: "Finger Millet Flour",
    category: "Grains",
    unit: "kg",
    photo: "millet flour",
    indivPrice: 55,
    bizPrice: 36,
    minBulkQty: 60,
    farmer: "Nagaraju H.S., Mandya",
  },
  {
    id: "p17",
    name: "Kutch Dates",
    category: "Fruits",
    unit: "kg",
    photo: "dates fruit",
    indivPrice: 480,
    bizPrice: 300,
    minBulkQty: 30,
    farmer: "Ismail Jat, Kutch",
  },
  {
    id: "p18",
    name: "Toor Dal",
    category: "Pulses",
    unit: "kg",
    photo: "lentils dal",
    indivPrice: 140,
    bizPrice: 95,
    minBulkQty: 40,
    farmer: "Sharad Deshmukh, Latur",
  },
  {
    id: "p19",
    name: "Chana Dal",
    category: "Pulses",
    unit: "kg",
    photo: "chickpea lentils",
    indivPrice: 95,
    bizPrice: 62,
    minBulkQty: 40,
    farmer: "Anil Chaudhary, Indore",
  },
  {
    id: "p20",
    name: "Moong Dal",
    category: "Pulses",
    unit: "kg",
    photo: "mung beans",
    indivPrice: 130,
    bizPrice: 85,
    minBulkQty: 40,
    farmer: "Rekha Sharma, Rajkot",
  },
  {
    id: "p21",
    name: "Masoor Dal",
    category: "Pulses",
    unit: "kg",
    photo: "red lentils",
    indivPrice: 110,
    bizPrice: 70,
    minBulkQty: 40,
    farmer: "Baldev Singh, Hisar",
  },
  {
    id: "p22",
    name: "Fresh Coriander",
    category: "Herbs",
    unit: "kg",
    photo: "coriander herb",
    indivPrice: 60,
    bizPrice: 35,
    minBulkQty: 20,
    farmer: "Ramesh Yadav, Pune",
  },
  {
    id: "p23",
    name: "Fresh Mint",
    category: "Herbs",
    unit: "kg",
    photo: "mint herb",
    indivPrice: 70,
    bizPrice: 40,
    minBulkQty: 15,
    farmer: "Suresh Vora, Ahmedabad",
  },
  {
    id: "p24",
    name: "Green Chillies",
    category: "Vegetables",
    unit: "kg",
    photo: "green chillies",
    indivPrice: 45,
    bizPrice: 28,
    minBulkQty: 30,
    farmer: "Farida Bee, Guntur",
  },
  {
    id: "p25",
    name: "Capsicum",
    category: "Vegetables",
    unit: "kg",
    photo: "bell pepper",
    indivPrice: 55,
    bizPrice: 34,
    minBulkQty: 30,
    farmer: "Manoj Bhandari, Bengaluru",
  },
  {
    id: "p26",
    name: "Cauliflower",
    category: "Vegetables",
    unit: "kg",
    photo: "cauliflower vegetable",
    indivPrice: 32,
    bizPrice: 20,
    minBulkQty: 40,
    farmer: "Iqbal Sandhu, Ludhiana",
  },
  {
    id: "p27",
    name: "Spinach",
    category: "Vegetables",
    unit: "kg",
    photo: "spinach leaves",
    indivPrice: 28,
    bizPrice: 17,
    minBulkQty: 35,
    farmer: "Kavita Rao, Hyderabad",
  },
  {
    id: "p28",
    name: "Bananas",
    category: "Fruits",
    unit: "dozen",
    photo: "bananas fruit",
    indivPrice: 55,
    bizPrice: 38,
    minBulkQty: 25,
    farmer: "Ganesh Naik, Jalgaon",
  },
  {
    id: "p29",
    name: "Green Grapes",
    category: "Fruits",
    unit: "kg",
    photo: "green grapes",
    indivPrice: 90,
    bizPrice: 60,
    minBulkQty: 30,
    farmer: "Vitthal Pawar, Nashik",
  },
  {
    id: "p30",
    name: "Tender Coconut",
    category: "Fruits",
    unit: "piece",
    photo: "coconut fruit",
    indivPrice: 35,
    bizPrice: 22,
    minBulkQty: 100,
    farmer: "Muthu Raman, Pollachi",
  },
  {
    id: "p31",
    name: "Groundnuts",
    category: "Nuts",
    unit: "kg",
    photo: "peanuts groundnut",
    indivPrice: 110,
    bizPrice: 72,
    minBulkQty: 40,
    farmer: "Digvijay Solanki, Rajkot",
  },
  {
    id: "p32",
    name: "Kashmiri Almonds",
    category: "Nuts",
    unit: "kg",
    photo: "almonds nuts",
    indivPrice: 850,
    bizPrice: 600,
    minBulkQty: 25,
    farmer: "Zorawar Bhatti, Kashmir",
  },
  {
    id: "p33",
    name: "Raisins",
    category: "Sweeteners",
    unit: "kg",
    photo: "raisins dried fruit",
    indivPrice: 320,
    bizPrice: 210,
    minBulkQty: 20,
    farmer: "Devraj Chavan, Nashik",
  },

  // Grains
  {
    id: "p34",
    name: "Basmati Rice",
    category: "Grains",
    unit: "kg",
    photo: "basmati rice",
    indivPrice: 120,
    bizPrice: 85,
    minBulkQty: 40,
    farmer: "Amarjit Gill, Karnal",
  },
  {
    id: "p35",
    name: "Pearl Millet (Bajra)",
    category: "Grains",
    unit: "kg",
    photo: "millet grain",
    indivPrice: 42,
    bizPrice: 28,
    minBulkQty: 60,
    farmer: "Deepak Chaudhary, Jodhpur",
  },
  {
    id: "p36",
    name: "Sorghum (Jowar)",
    category: "Grains",
    unit: "kg",
    photo: "sorghum grain",
    indivPrice: 44,
    bizPrice: 30,
    minBulkQty: 60,
    farmer: "Yogesh Patil, Solapur",
  },
  {
    id: "p37",
    name: "Barley",
    category: "Grains",
    unit: "kg",
    photo: "barley grain",
    indivPrice: 40,
    bizPrice: 27,
    minBulkQty: 60,
    farmer: "Harveen Brar, Amritsar",
  },
  {
    id: "p38",
    name: "Sweet Corn",
    category: "Grains",
    unit: "kg",
    photo: "corn maize",
    indivPrice: 35,
    bizPrice: 22,
    minBulkQty: 50,
    farmer: "Mahesh Jadhav, Nashik",
  },

  // Oils
  {
    id: "p39",
    name: "Groundnut Oil",
    category: "Oils",
    unit: "litre",
    photo: "peanut oil bottle",
    indivPrice: 195,
    bizPrice: 150,
    minBulkQty: 20,
    farmer: "Ketan Vaghela, Junagadh",
  },
  {
    id: "p40",
    name: "Sunflower Oil",
    category: "Oils",
    unit: "litre",
    photo: "sunflower oil bottle",
    indivPrice: 165,
    bizPrice: 125,
    minBulkQty: 20,
    farmer: "Ramanna Gowda, Bellary",
  },
  {
    id: "p41",
    name: "Virgin Coconut Oil",
    category: "Oils",
    unit: "litre",
    photo: "coconut oil bottle",
    indivPrice: 320,
    bizPrice: 240,
    minBulkQty: 15,
    farmer: "Sherin Thomas, Kochi",
  },
  {
    id: "p42",
    name: "Sesame (Til) Oil",
    category: "Oils",
    unit: "litre",
    photo: "sesame oil bottle",
    indivPrice: 260,
    bizPrice: 195,
    minBulkQty: 15,
    farmer: "Chandrakant Naik, Latur",
  },
  {
    id: "p43",
    name: "Cold-Pressed Olive Oil",
    category: "Oils",
    unit: "litre",
    photo: "olive oil bottle",
    indivPrice: 780,
    bizPrice: 590,
    minBulkQty: 10,
    farmer: "Nilgiri Growers Co-op, Coimbatore",
  },

  // Fruits
  {
    id: "p44",
    name: "Himachal Apples",
    category: "Fruits",
    unit: "kg",
    photo: "red apples",
    indivPrice: 180,
    bizPrice: 130,
    minBulkQty: 25,
    farmer: "Rohit Thakur, Shimla",
  },
  {
    id: "p45",
    name: "Nagpur Oranges",
    category: "Fruits",
    unit: "kg",
    photo: "oranges citrus",
    indivPrice: 90,
    bizPrice: 62,
    minBulkQty: 30,
    farmer: "Sanjay Deshmukh, Nagpur",
  },
  {
    id: "p46",
    name: "Pomegranate",
    category: "Fruits",
    unit: "kg",
    photo: "pomegranate fruit",
    indivPrice: 150,
    bizPrice: 105,
    minBulkQty: 25,
    farmer: "Vishal Chavan, Solapur",
  },
  {
    id: "p47",
    name: "Watermelon",
    category: "Fruits",
    unit: "piece",
    photo: "watermelon",
    indivPrice: 60,
    bizPrice: 40,
    minBulkQty: 40,
    farmer: "Irfan Shaikh, Karnal",
  },
  {
    id: "p48",
    name: "Papaya",
    category: "Fruits",
    unit: "kg",
    photo: "papaya fruit",
    indivPrice: 45,
    bizPrice: 28,
    minBulkQty: 40,
    farmer: "Lakshman Nair, Salem",
  },
  {
    id: "p49",
    name: "Guava",
    category: "Fruits",
    unit: "kg",
    photo: "guava fruit",
    indivPrice: 65,
    bizPrice: 42,
    minBulkQty: 30,
    farmer: "Om Prakash, Allahabad",
  },
  {
    id: "p50",
    name: "Pineapple",
    category: "Fruits",
    unit: "piece",
    photo: "pineapple fruit",
    indivPrice: 55,
    bizPrice: 36,
    minBulkQty: 30,
    farmer: "Bimol Das, Tripura",
  },
  {
    id: "p51",
    name: "Litchi",
    category: "Fruits",
    unit: "kg",
    photo: "lychee fruit",
    indivPrice: 220,
    bizPrice: 150,
    minBulkQty: 20,
    farmer: "Anand Jha, Muzaffarpur",
  },

  // Vegetables
  {
    id: "p52",
    name: "Carrots",
    category: "Vegetables",
    unit: "kg",
    photo: "carrots vegetable",
    indivPrice: 40,
    bizPrice: 25,
    minBulkQty: 40,
    farmer: "Balraj Sandhu, Ludhiana",
  },
  {
    id: "p53",
    name: "Cabbage",
    category: "Vegetables",
    unit: "kg",
    photo: "cabbage vegetable",
    indivPrice: 25,
    bizPrice: 15,
    minBulkQty: 45,
    farmer: "Sunil Wagh, Pune",
  },
  {
    id: "p54",
    name: "Brinjal (Eggplant)",
    category: "Vegetables",
    unit: "kg",
    photo: "eggplant brinjal",
    indivPrice: 35,
    bizPrice: 22,
    minBulkQty: 35,
    farmer: "Rajendra Naik, Nagpur",
  },
  {
    id: "p55",
    name: "Beetroot",
    category: "Vegetables",
    unit: "kg",
    photo: "beetroot vegetable",
    indivPrice: 38,
    bizPrice: 24,
    minBulkQty: 30,
    farmer: "Simran Kaur, Jalandhar",
  },
  {
    id: "p56",
    name: "Green Peas",
    category: "Vegetables",
    unit: "kg",
    photo: "green peas",
    indivPrice: 70,
    bizPrice: 46,
    minBulkQty: 25,
    farmer: "Devendra Kushwaha, Agra",
  },
  {
    id: "p57",
    name: "Okra (Bhindi)",
    category: "Vegetables",
    unit: "kg",
    photo: "okra vegetable",
    indivPrice: 42,
    bizPrice: 27,
    minBulkQty: 30,
    farmer: "Fatima Sheikh, Hyderabad",
  },
  {
    id: "p58",
    name: "Cucumber",
    category: "Vegetables",
    unit: "kg",
    photo: "cucumber vegetable",
    indivPrice: 30,
    bizPrice: 18,
    minBulkQty: 35,
    farmer: "Ajay Mali, Nashik",
  },
  {
    id: "p59",
    name: "Pumpkin",
    category: "Vegetables",
    unit: "kg",
    photo: "pumpkin vegetable",
    indivPrice: 28,
    bizPrice: 17,
    minBulkQty: 40,
    farmer: "Geeta Bhoi, Raipur",
  },
  {
    id: "p60",
    name: "Radish",
    category: "Vegetables",
    unit: "kg",
    photo: "radish vegetable",
    indivPrice: 24,
    bizPrice: 15,
    minBulkQty: 35,
    farmer: "Harpal Randhawa, Jalandhar",
  },
  {
    id: "p61",
    name: "Bitter Gourd",
    category: "Vegetables",
    unit: "kg",
    photo: "bitter gourd vegetable",
    indivPrice: 46,
    bizPrice: 30,
    minBulkQty: 25,
    farmer: "Kumari Bai, Bhopal",
  },
];

const CATEGORY_OPTIONS = [
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
const UNIT_OPTIONS = ["kg", "g", "litre", "ml", "dozen", "piece"];
const MAX_SAVER_THRESHOLD = 35; // % discount to qualify as a Max Saver deal

function discountPct(p) {
  return Math.round(((p.indivPrice - p.bizPrice) / p.indivPrice) * 100);
}

function isGstinValid(g) {
  return /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(
    g.trim().toUpperCase(),
  );
}

const money = (n) => `₹${Number(n || 0).toLocaleString("en-IN")}`;

// Real photos. Farmer-uploaded products carry their own image as a data URL
// (see the file input in FarmerPortal). Everything else gets a real photograph
// from Picsum's CDN, seeded per-product so the same item always shows the same
// photo — Picsum is a plain, reliable image host with no keys, rate limits, or
// CORS issues, unlike keyword-matched services which can go down or throttle.
function photoUrl(product, w = 480, h = 360) {
  const seed = encodeURIComponent(product.photo || product.id);
  return `https://picsum.photos/seed/${seed}/${w}/${h}`;
}

// ---------------------------------------------------------------------------
// Deterministic "fake backend" content for the product detail page —
// seeded off the product id so the same product always shows the same
// description, rating and reviews (no backend, but stable across renders).
// ---------------------------------------------------------------------------

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
  "Anjali M.",
  "Rohan D.",
  "Priya S.",
  "Karan V.",
  "Meera J.",
  "Arjun K.",
  "Sneha R.",
  "Vikram T.",
  "Divya N.",
  "Sameer P.",
  "Ritu B.",
  "Faisal A.",
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

function generateDescription(product) {
  const rnd = seededRandom(product.id + product.name);
  const notes = [
    "sun-ripened",
    "hand-picked",
    "carefully sorted",
    "harvest-fresh",
    "traditionally grown",
    "small-batch",
  ];
  const uses = [
    "everyday cooking",
    "festive meals",
    "your kitchen staples",
    "bulk meal prep",
    "gifting and home use",
  ];
  const note = notes[Math.floor(rnd() * notes.length)];
  const use = uses[Math.floor(rnd() * uses.length)];
  return `${note[0].toUpperCase()}${note.slice(1)} ${product.name.toLowerCase()} sourced directly from ${product.farmer}, grown in the ${product.category.toLowerCase()} belt of their region. Sold by the ${product.unit}, it's a favorite for ${use}. Buying direct means the farmer earns a fairer share and you skip the middlemen markup — households pay ${money(
    product.indivPrice,
  )}/${product.unit}, while verified businesses ordering at least ${product.minBulkQty} ${product.unit} unlock the bulk rate of ${money(product.bizPrice)}/${product.unit}.`;
}

function generateReviews(product) {
  const rnd = seededRandom("rev-" + product.id);
  const count = 3 + Math.floor(rnd() * 4); // 3-6 reviews
  const reviews = [];
  const usedNames = new Set();
  for (let i = 0; i < count; i++) {
    let name = REVIEW_NAMES[Math.floor(rnd() * REVIEW_NAMES.length)];
    while (usedNames.has(name) && usedNames.size < REVIEW_NAMES.length) {
      name = REVIEW_NAMES[Math.floor(rnd() * REVIEW_NAMES.length)];
    }
    usedNames.add(name);
    const rating = Math.min(5, 3 + Math.round(rnd() * 2)); // 3-5 stars
    const template =
      REVIEW_TEMPLATES[Math.floor(rnd() * REVIEW_TEMPLATES.length)];
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

function avgRating(reviews) {
  if (!reviews.length) return 0;
  return reviews.reduce((s, r) => s + r.rating, 0) / reviews.length;
}

function timeAgo(days) {
  if (days < 1) return "today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  const months = Math.round(days / 30);
  return months === 1 ? "1 month ago" : `${months} months ago`;
}

function StarRow({ rating, size = "w-3.5 h-3.5" }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={`${size} ${
            n <= Math.round(rating)
              ? "fill-[#C9A227] text-[#C9A227]"
              : "text-[#D8CBA1]"
          }`}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root component — role gate
// ---------------------------------------------------------------------------

export default function FarmMarketplace() {
  const [role, setRole] = usePersistentState("ks_role", null); // null | 'consumer' | 'farmer'
  const [farmerProducts, setFarmerProducts] = usePersistentState(
    "ks_farmerProducts",
    [],
  );

  const allProducts = useMemo(
    () => [...farmerProducts, ...PRODUCTS],
    [farmerProducts],
  );

  function addFarmerProduct(product) {
    setFarmerProducts((list) => [product, ...list]);
  }

  function removeFarmerProduct(id) {
    setFarmerProducts((list) => list.filter((p) => p.id !== id));
  }

  if (!role) return <RoleGate onSelect={setRole} />;

  if (role === "farmer") {
    return (
      <FarmerPortal
        listings={farmerProducts}
        onAdd={addFarmerProduct}
        onRemove={removeFarmerProduct}
        onSwitch={() => setRole(null)}
      />
    );
  }

  return (
    <ConsumerMarketplace
      allProducts={allProducts}
      onSwitch={() => setRole(null)}
    />
  );
}

// ---------------------------------------------------------------------------
// Role gate (landing page)
// ---------------------------------------------------------------------------

function RoleGate({ onSelect }) {
  return (
    <div
      className="min-h-screen w-full bg-[#14140F] text-[#F3ECDD] flex items-center justify-center px-5"
      style={{
        fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
        .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
      `}</style>

      <div className="max-w-3xl w-full py-16">
        <div className="flex items-center gap-2 justify-center mb-3">
          <Leaf className="w-6 h-6 text-[#C9A227]" strokeWidth={1.75} />
          <span className="ff-display text-2xl tracking-tight">
            Kheti Seedha
          </span>
        </div>
        <h1 className="ff-display text-3xl sm:text-4xl text-center leading-[1.15]">
          Who's joining today?
        </h1>
        <p className="text-center text-[15px] text-[#C9C3AE] mt-3 max-w-md mx-auto">
          Farmers list what they've harvested. Households and businesses buy it
          direct — no middlemen.
        </p>

        <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-5">
          <button
            onClick={() => onSelect("farmer")}
            className="group text-left border border-[#33301F] bg-[#1D1C14] hover:border-[#C9A227] transition-colors p-6"
          >
            <Sprout className="w-8 h-8 text-[#C9A227]" strokeWidth={1.5} />
            <h2 className="ff-display text-2xl mt-4">I'm a Farmer</h2>
            <p className="text-sm text-[#C9C3AE] mt-2 leading-relaxed">
              List your grains, oils, fruits and vegetables so households and
              bulk buyers can order straight from you.
            </p>
            <span className="inline-flex items-center gap-1 text-sm text-[#C9A227] mt-4 group-hover:gap-2 transition-all">
              Start selling →
            </span>
          </button>

          <button
            onClick={() => onSelect("consumer")}
            className="group text-left border border-[#33301F] bg-[#1D1C14] hover:border-[#C9A227] transition-colors p-6"
          >
            <Store className="w-8 h-8 text-[#C9A227]" strokeWidth={1.5} />
            <h2 className="ff-display text-2xl mt-4">I'm a Consumer</h2>
            <p className="text-sm text-[#C9C3AE] mt-2 leading-relaxed">
              Shop farm-direct produce at a fair household price, or unlock bulk
              business rates with your GSTIN.
            </p>
            <span className="inline-flex items-center gap-1 text-sm text-[#C9A227] mt-4 group-hover:gap-2 transition-all">
              Browse the market →
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Farmer portal — add & manage listings
// ---------------------------------------------------------------------------

const EMPTY_FORM = {
  name: "",
  category: "Grains",
  unit: "kg",
  indivPrice: "",
  bizPrice: "",
  minBulkQty: "",
  farmerName: "",
  location: "",
  imageData: null,
  imageName: "",
};

const MAX_IMAGE_BYTES = 20 * 1024 * 1024; // 4MB

function FarmerPortal({ listings, onAdd, onRemove, onSwitch }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [toast, setToast] = useState(null);

  function flashToast(msg) {
    setToast(msg);
    window.clearTimeout(flashToast._t);
    flashToast._t = window.setTimeout(() => setToast(null), 2200);
  }

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handlePhotoChange(ev) {
    const file = ev.target.files && ev.target.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setErrors((e) => ({ ...e, image: "Please choose an image file" }));
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setErrors((e) => ({
        ...e,
        image: "Image is too large — please use one under 20MB",
      }));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setForm((f) => ({
        ...f,
        imageData: reader.result,
        imageName: file.name,
      }));
      setErrors((e) => ({ ...e, image: undefined }));
    };
    reader.onerror = () => {
      setErrors((e) => ({
        ...e,
        image: "Couldn't read that image — try another file",
      }));
    };
    reader.readAsDataURL(file);
  }

  function clearPhoto() {
    setForm((f) => ({ ...f, imageData: null, imageName: "" }));
  }

  function validate() {
    const e = {};
    if (!form.name.trim()) e.name = "Enter a product name";
    if (!form.indivPrice || Number(form.indivPrice) <= 0)
      e.indivPrice = "Enter a household price";
    if (!form.bizPrice || Number(form.bizPrice) <= 0)
      e.bizPrice = "Enter a bulk/business price";
    if (
      form.bizPrice &&
      form.indivPrice &&
      Number(form.bizPrice) >= Number(form.indivPrice)
    )
      e.bizPrice = "Bulk price should be lower than household price";
    if (!form.minBulkQty || Number(form.minBulkQty) <= 0)
      e.minBulkQty = "Enter a minimum bulk quantity";
    if (!form.farmerName.trim()) e.farmerName = "Enter your name";
    if (!form.location.trim()) e.location = "Enter your village/district";
    return e;
  }

  function handleSubmit(ev) {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length > 0) return;

    const product = {
      id: `f-${Date.now()}`,
      name: form.name.trim(),
      category: form.category,
      unit: form.unit,
      photo: `${form.name} ${form.category}`,
      imageData: form.imageData || null,
      indivPrice: Number(form.indivPrice),
      bizPrice: Number(form.bizPrice),
      minBulkQty: Number(form.minBulkQty),
      farmer: `${form.farmerName.trim()}, ${form.location.trim()}`,
      farmerAdded: true,
    };
    onAdd(product);
    flashToast(`${product.name} is now live for consumers`);
    setForm((f) => ({
      ...EMPTY_FORM,
      farmerName: f.farmerName,
      location: f.location,
    }));
  }

  return (
    <div
      className="min-h-screen w-full bg-[#F3ECDD] text-[#2A2820]"
      style={{
        fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
        .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
        .tabular { font-variant-numeric: tabular-nums; }
      `}</style>

      <div className="bg-[#14140F] text-[#F3ECDD]">
        <header className="border-b border-[#33301F]">
          <div className="max-w-6xl mx-auto px-5 py-5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Leaf className="w-6 h-6 text-[#C9A227]" strokeWidth={1.75} />
              <span className="ff-display text-2xl tracking-tight">
                Kheti Seedha
              </span>
              <span className="ml-2 text-[11px] uppercase tracking-wide border border-[#C9A227] text-[#C9A227] px-2 py-0.5">
                Farmer portal
              </span>
            </div>
            <button
              onClick={onSwitch}
              className="flex items-center gap-1.5 px-3 py-2 text-sm border border-[#4A4630] text-[#C9C3AE] hover:border-[#C9A227] hover:text-[#C9A227] transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Switch role
            </button>
          </div>
        </header>
        <section className="max-w-6xl mx-auto px-5 pt-10 pb-8">
          <h1 className="ff-display text-3xl sm:text-4xl leading-[1.1] max-w-xl">
            List a new product for consumers
          </h1>
          <p className="mt-3 text-[15px] text-[#C9C3AE] max-w-lg">
            Set a fair household price and a discounted bulk rate for
            businesses. It appears in the consumer marketplace the moment you
            publish it.
          </p>
        </section>
      </div>

      <main className="max-w-6xl mx-auto px-5 py-8 grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Add product form */}
        <form
          onSubmit={handleSubmit}
          className="lg:col-span-2 border border-[#E4D6A7] bg-[#FBF7EC] p-5 h-fit"
        >
          <h2 className="ff-display text-xl flex items-center gap-2">
            <PackagePlus className="w-5 h-5 text-[#1B3A2B]" /> Product details
          </h2>

          <Field label="Product name" error={errors.name}>
            <input
              value={form.name}
              onChange={(e) => update("name", e.target.value)}
              placeholder="e.g. Sona Masoori Rice"
              className="fm-input"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Category">
              <select
                value={form.category}
                onChange={(e) => update("category", e.target.value)}
                className="fm-input"
              >
                {CATEGORY_OPTIONS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Unit">
              <select
                value={form.unit}
                onChange={(e) => update("unit", e.target.value)}
                className="fm-input"
              >
                {UNIT_OPTIONS.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Household price (₹)" error={errors.indivPrice}>
              <input
                type="number"
                min="0"
                value={form.indivPrice}
                onChange={(e) => update("indivPrice", e.target.value)}
                placeholder="62"
                className="fm-input"
              />
            </Field>
            <Field label="Bulk/business price (₹)" error={errors.bizPrice}>
              <input
                type="number"
                min="0"
                value={form.bizPrice}
                onChange={(e) => update("bizPrice", e.target.value)}
                placeholder="42"
                className="fm-input"
              />
            </Field>
          </div>

          <Field label="Minimum bulk order quantity" error={errors.minBulkQty}>
            <input
              type="number"
              min="0"
              value={form.minBulkQty}
              onChange={(e) => update("minBulkQty", e.target.value)}
              placeholder="50"
              className="fm-input"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Your name" error={errors.farmerName}>
              <input
                value={form.farmerName}
                onChange={(e) => update("farmerName", e.target.value)}
                placeholder="Ravi Kumar"
                className="fm-input"
              />
            </Field>
            <Field label="Village / district" error={errors.location}>
              <input
                value={form.location}
                onChange={(e) => update("location", e.target.value)}
                placeholder="Nalgonda"
                className="fm-input"
              />
            </Field>
          </div>

          <Field label="Product photo" error={errors.image}>
            {form.imageData ? (
              <div className="flex items-center gap-3">
                <img
                  src={form.imageData}
                  alt="Preview"
                  className="w-20 h-20 object-cover border border-[#D8CBA1]"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-[#5C5842] truncate">
                    {form.imageName}
                  </p>
                  <button
                    type="button"
                    onClick={clearPhoto}
                    className="text-xs text-[#8C2E33] hover:text-[#6B1E2B] mt-1"
                  >
                    Remove photo
                  </button>
                </div>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center gap-1.5 border border-dashed border-[#D8CBA1] bg-white py-5 text-center cursor-pointer hover:border-[#1B3A2B]">
                <Camera className="w-5 h-5 text-[#8A8468]" />
                <span className="text-xs text-[#5C5842]">
                  Tap to upload a photo of your product (under 20MB)
                </span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoChange}
                  className="hidden"
                />
              </label>
            )}
            <p className="text-[11px] text-[#8A8468] mt-1">
              No photo? A placeholder image is used until you add one.
            </p>
          </Field>

          <button
            type="submit"
            className="w-full mt-4 py-2.5 bg-[#1B3A2B] text-[#F3ECDD] text-sm hover:bg-[#14140F] active:bg-[#0E1F17] transition-colors"
          >
            Publish product
          </button>

          <style>{`
            .fm-input {
              width: 100%;
              border: 1px solid #D8CBA1;
              background: #FFFFFF;
              padding: 0.5rem 0.65rem;
              font-size: 0.875rem;
              outline: none;
            }
            .fm-input:focus { border-color: #1B3A2B; }
          `}</style>
        </form>

        {/* Your live listings */}
        <div className="lg:col-span-3">
          <h2 className="ff-display text-xl mb-3">
            Your live listings{" "}
            {listings.length > 0 && (
              <span className="text-sm text-[#5C5842]">
                ({listings.length})
              </span>
            )}
          </h2>
          {listings.length === 0 ? (
            <p className="text-sm text-[#5C5842] border border-dashed border-[#D8CBA1] p-6 text-center">
              Nothing published yet — add your first product on the left.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {listings.map((p) => (
                <div
                  key={p.id}
                  className="border border-[#E4D6A7] bg-[#FBF7EC] flex flex-col"
                >
                  <ProductPhoto
                    product={p}
                    className="w-full h-32 object-cover"
                  />
                  <div className="p-3 flex-1 flex flex-col">
                    <h3 className="ff-display text-base leading-snug">
                      {p.name}
                    </h3>
                    <p className="text-[11px] text-[#5C5842]">
                      {p.category} · {p.unit}
                    </p>
                    <p className="text-sm tabular mt-1 text-[#1B3A2B]">
                      {money(p.indivPrice)}{" "}
                      <span className="text-[#5C5842]">household</span>
                    </p>
                    <p className="text-xs tabular text-[#8A6D1E]">
                      {money(p.bizPrice)} bulk · min {p.minBulkQty} {p.unit}
                    </p>
                    <button
                      onClick={() => onRemove(p.id)}
                      className="mt-auto pt-2 flex items-center gap-1 text-xs text-[#8C2E33] hover:text-[#6B1E2B]"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Remove listing
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {toast && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 bg-[#14140F] text-[#F3ECDD] text-sm px-4 py-2.5 flex items-center gap-2 shadow-lg border border-[#C9A227]/40 z-50">
          {toast}
          <button onClick={() => setToast(null)}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

function Field({ label, error, children }) {
  return (
    <label className="block mt-4 text-sm">
      <span className="block text-[#5C5842] mb-1">{label}</span>
      {children}
      {error && (
        <span className="block text-xs text-[#C4544A] mt-1">{error}</span>
      )}
    </label>
  );
}

// ---------------------------------------------------------------------------
// Consumer marketplace
// ---------------------------------------------------------------------------

function ConsumerMarketplace({ allProducts, onSwitch }) {
  const [consumerType, setConsumerType] = usePersistentState(
    "ks_consumerType",
    "individual",
  ); // 'individual' | 'business'
  const [gstin, setGstin] = usePersistentState("ks_gstin", "");
  const [gstinTouched, setGstinTouched] = useState(false);
  const [category, setCategory] = usePersistentState("ks_category", "All");
  const [maxSaverOnly, setMaxSaverOnly] = usePersistentState(
    "ks_maxSaverOnly",
    false,
  );
  const [cart, setCart] = usePersistentState("ks_cart", {}); // id -> qty
  const [view, setView] = useState("shop"); // 'shop' | 'cart' | 'product'
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [toast, setToast] = useState(null);

  const isBusiness = consumerType === "business";
  const gstinOk = isGstinValid(gstin);
  const bizUnlocked = isBusiness && gstinOk;

  const categories = useMemo(
    () => ["All", ...Array.from(new Set(allProducts.map((p) => p.category)))],
    [allProducts],
  );

  const visibleProducts = useMemo(() => {
    let list = allProducts;
    if (category !== "All") list = list.filter((p) => p.category === category);
    if (isBusiness && maxSaverOnly)
      list = list.filter((p) => discountPct(p) >= MAX_SAVER_THRESHOLD);
    return list;
  }, [allProducts, category, isBusiness, maxSaverOnly]);

  function flashToast(msg) {
    setToast(msg);
    window.clearTimeout(flashToast._t);
    flashToast._t = window.setTimeout(() => setToast(null), 2200);
  }

  function addToCart(product) {
    if (isBusiness && !bizUnlocked) {
      flashToast("Add a valid GSTIN to unlock business pricing");
      return;
    }
    const startQty = isBusiness ? product.minBulkQty : 1;
    setCart((c) => ({ ...c, [product.id]: (c[product.id] || 0) + startQty }));
    flashToast(
      isBusiness
        ? `${product.name} bulk order added`
        : `${product.name} added to your order`,
    );
  }

  function setQty(product, qty) {
    const floor = isBusiness ? product.minBulkQty : 1;
    const clean = Math.max(0, qty);
    setCart((c) => {
      const next = { ...c };
      if (clean <= 0) {
        delete next[product.id];
      } else {
        next[product.id] = clean < floor ? floor : clean;
      }
      return next;
    });
  }

  function removeFromCart(id) {
    setCart((c) => {
      const next = { ...c };
      delete next[id];
      return next;
    });
  }

  function openProduct(product) {
    setSelectedProductId(product.id);
    setView("product");
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  const selectedProduct = selectedProductId
    ? allProducts.find((p) => p.id === selectedProductId)
    : null;

  const cartLines = Object.entries(cart)
    .map(([id, qty]) => ({
      product: allProducts.find((p) => p.id === id),
      qty,
    }))
    .filter((l) => l.product);

  const priceFor = (p) => (bizUnlocked ? p.bizPrice : p.indivPrice);
  const subtotal = cartLines.reduce(
    (sum, l) => sum + priceFor(l.product) * l.qty,
    0,
  );
  const savings = bizUnlocked
    ? cartLines.reduce(
        (sum, l) => sum + (l.product.indivPrice - l.product.bizPrice) * l.qty,
        0,
      )
    : 0;

  return (
    <div
      className="min-h-screen w-full bg-[#F3ECDD] text-[#2A2820]"
      style={{
        fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
        .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
        .tabular { font-variant-numeric: tabular-nums; }
      `}</style>

      {/* ---------------------------------------------------------------- */}
      {/* Header + Hero (onyx, gold accents)                               */}
      {/* ---------------------------------------------------------------- */}
      <div className="bg-[#14140F] text-[#F3ECDD]">
        <header className="border-b border-[#33301F]">
          <div className="max-w-6xl mx-auto px-5 py-5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Leaf className="w-6 h-6 text-[#C9A227]" strokeWidth={1.75} />
              <span className="ff-display text-2xl tracking-tight">
                Kheti Seedha
              </span>
            </div>
            <div className="hidden sm:flex items-center gap-3">
              <button
                onClick={onSwitch}
                className="flex items-center gap-1.5 px-3 py-2 text-sm border border-[#4A4630] text-[#C9C3AE] hover:border-[#C9A227] hover:text-[#C9A227] transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Switch role
              </button>
              <ConsumerToggle
                consumerType={consumerType}
                onChange={(t) => setConsumerType(t)}
              />
              <CartButton
                count={cartLines.length}
                active={view === "cart"}
                onClick={() => setView(view === "cart" ? "shop" : "cart")}
              />
            </div>
          </div>
          <div className="sm:hidden max-w-6xl mx-auto px-5 pb-4 flex items-center gap-2">
            <button
              onClick={onSwitch}
              className="flex items-center justify-center px-2.5 py-2 text-sm border border-[#4A4630] text-[#C9C3AE]"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
            </button>
            <div className="flex-1">
              <ConsumerToggle
                consumerType={consumerType}
                onChange={(t) => setConsumerType(t)}
              />
            </div>
            <CartButton
              count={cartLines.length}
              active={view === "cart"}
              onClick={() => setView(view === "cart" ? "shop" : "cart")}
            />
          </div>
        </header>

        {view === "shop" && (
          <section className="max-w-6xl mx-auto px-5 pt-12 pb-10">
            <div className="max-w-xl">
              <h1 className="ff-display text-4xl sm:text-5xl leading-[1.08] text-[#F3ECDD]">
                Straight from the field, priced for who's buying.
              </h1>
              <p className="mt-4 text-[15px] leading-relaxed text-[#C9C3AE] max-w-md">
                Households pay a fair per-unit price. Registered businesses
                buying in bulk get farmer-direct rates on premium produce — no
                middlemen, just a valid GSTIN and a minimum order size.
              </p>
            </div>

            {isBusiness && (
              <div className="mt-8 max-w-md border border-[#33301F] bg-[#1D1C14] p-4">
                <label className="block text-sm text-[#C9C3AE] mb-2">
                  GSTIN{" "}
                  <span className="text-[#C9A227]">
                    — required for business pricing
                  </span>
                </label>
                <div className="flex gap-2">
                  <input
                    value={gstin}
                    onChange={(e) => setGstin(e.target.value.toUpperCase())}
                    onBlur={() => setGstinTouched(true)}
                    placeholder="22AAAAA0000A1Z5"
                    maxLength={15}
                    className="flex-1 border border-[#4A4630] bg-[#14140F] text-[#F3ECDD] px-3 py-2 text-sm tracking-wide outline-none focus:border-[#C9A227]"
                  />
                  {gstinOk ? (
                    <span className="flex items-center gap-1 text-sm text-[#C9A227] px-2">
                      <CheckCircle2 className="w-4 h-4" /> Verified
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-sm text-[#8A8468] px-2">
                      <Lock className="w-4 h-4" /> Locked
                    </span>
                  )}
                </div>
                {gstinTouched && !gstinOk && gstin.length > 0 && (
                  <p className="mt-2 text-xs text-[#C4544A]">
                    That doesn't look like a valid 15-character GSTIN yet.
                  </p>
                )}
              </div>
            )}
          </section>
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Filter bar                                                       */}
      {/* ---------------------------------------------------------------- */}
      {view === "shop" && (
        <section className="max-w-6xl mx-auto px-5 sticky top-0 z-10 bg-[#F3ECDD]/95 backdrop-blur border-y border-[#E4D6A7] py-3 flex flex-wrap items-center gap-2">
          {categories.map((c) => {
            const active = category === c;
            return (
              <button
                key={c}
                onClick={() => setCategory(c)}
                aria-pressed={active}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm border transition-colors ${
                  active
                    ? "bg-[#1B3A2B] border-[#1B3A2B] text-[#F3ECDD] shadow-[inset_0_0_0_1px_#C9A227]"
                    : "bg-transparent border-[#D8CBA1] text-[#5C5842] hover:border-[#1B3A2B] hover:text-[#1B3A2B]"
                }`}
              >
                {active && (
                  <span className="w-1.5 h-1.5 rounded-full bg-[#C9A227]" />
                )}
                {c}
              </button>
            );
          })}

          {isBusiness && (
            <button
              onClick={() => setMaxSaverOnly((v) => !v)}
              disabled={!bizUnlocked}
              aria-pressed={maxSaverOnly}
              title={
                !bizUnlocked ? "Verify your GSTIN to use Max Saver" : undefined
              }
              className={`ml-auto flex items-center gap-1.5 px-3 py-1.5 text-sm border transition-colors ${
                maxSaverOnly
                  ? "bg-[#C9A227] border-[#C9A227] text-[#14140F] shadow-[inset_0_0_0_1px_#14140F]"
                  : "bg-transparent border-[#C9A227] text-[#8A6D1E]"
              } ${!bizUnlocked ? "opacity-40 cursor-not-allowed" : "hover:bg-[#C9A227]/15"}`}
            >
              <BadgePercent className="w-4 h-4" />
              Max Saver deals only
            </button>
          )}
        </section>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Product grid                                                     */}
      {/* ---------------------------------------------------------------- */}
      {view === "shop" && (
        <main className="max-w-6xl mx-auto px-5 py-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {visibleProducts.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                isBusiness={isBusiness}
                bizUnlocked={bizUnlocked}
                qtyInCart={cart[p.id] || 0}
                onAdd={() => addToCart(p)}
                onSetQty={(q) => setQty(p, q)}
                onOpen={() => openProduct(p)}
              />
            ))}
            {visibleProducts.length === 0 && (
              <p className="col-span-full text-sm text-[#5C5842] py-10 text-center">
                No products match this filter yet.
              </p>
            )}
          </div>
        </main>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Cart page                                                        */}
      {/* ---------------------------------------------------------------- */}
      {view === "cart" && (
        <CartPage
          cartLines={cartLines}
          isBusiness={isBusiness}
          bizUnlocked={bizUnlocked}
          priceFor={priceFor}
          subtotal={subtotal}
          savings={savings}
          bizUnlockedSavings={bizUnlocked && savings > 0}
          setQty={setQty}
          removeFromCart={removeFromCart}
          onBack={() => setView("shop")}
        />
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Product detail page                                              */}
      {/* ---------------------------------------------------------------- */}
      {view === "product" && selectedProduct && (
        <ProductDetailPage
          product={selectedProduct}
          allProducts={allProducts}
          cart={cart}
          isBusiness={isBusiness}
          bizUnlocked={bizUnlocked}
          onAddToCart={addToCart}
          onSetQty={setQty}
          onBack={() => setView("shop")}
          onOpenProduct={openProduct}
        />
      )}

      {toast && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 bg-[#14140F] text-[#F3ECDD] text-sm px-4 py-2.5 flex items-center gap-2 shadow-lg border border-[#C9A227]/40 z-50">
          {toast}
          <button onClick={() => setToast(null)}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------

function ProductPhoto({ product, className }) {
  const [failed, setFailed] = useState(false);
  // A farmer-uploaded photo (base64 data URL) always takes priority.
  const src = product.imageData || photoUrl(product);

  if (failed) {
    return (
      <div
        className={`${className} bg-[#EDE4C8] flex items-center justify-center text-[#8A8468]`}
      >
        <ImageOff className="w-5 h-5" />
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={product.name}
      loading="lazy"
      onError={() => setFailed(true)}
      className={className}
    />
  );
}

function CartPage({
  cartLines,
  isBusiness,
  bizUnlocked,
  priceFor,
  subtotal,
  savings,
  bizUnlockedSavings,
  setQty,
  removeFromCart,
  onBack,
}) {
  return (
    <main className="max-w-3xl mx-auto px-5 py-10">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[#5C5842] hover:text-[#1B3A2B] transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Continue shopping
      </button>

      <div className="flex items-center gap-2 mt-6 mb-6">
        <ShoppingCart className="w-5 h-5 text-[#1B3A2B]" />
        <h1 className="ff-display text-3xl">Your order</h1>
      </div>

      {cartLines.length === 0 ? (
        <div className="border border-[#E4D6A7] bg-[#FBF7EC] px-6 py-16 text-center">
          <p className="text-sm text-[#5C5842]">
            Nothing added yet — head back to the catalogue to start an order.
          </p>
          <button
            onClick={onBack}
            className="mt-4 px-4 py-2 text-sm border border-[#1B3A2B] text-[#1B3A2B] hover:bg-[#1B3A2B] hover:text-[#F3ECDD] transition-colors"
          >
            Browse products
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-4">
            {cartLines.map(({ product, qty }) => (
              <div
                key={product.id}
                className="flex items-start gap-3 text-sm border border-[#E4D6A7] bg-[#FBF7EC] p-3"
              >
                <ProductPhoto
                  product={product}
                  className="w-16 h-16 object-cover shrink-0"
                />
                <div className="flex-1">
                  <p className="ff-display text-base leading-tight">
                    {product.name}
                  </p>
                  <p className="text-xs text-[#5C5842] mt-1">
                    {product.farmer}
                  </p>
                  <p className="text-xs text-[#5C5842] tabular mt-1">
                    {qty} {product.unit} × {money(priceFor(product))}
                  </p>
                  {isBusiness && (
                    <p className="text-[11px] text-[#8A6D1E] mt-0.5">
                      Min order {product.minBulkQty} {product.unit}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setQty(product, qty - (isBusiness ? 5 : 1))}
                    className="w-7 h-7 flex items-center justify-center border border-[#D8CBA1] hover:border-[#1B3A2B] active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                  >
                    <Minus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setQty(product, qty + (isBusiness ? 5 : 1))}
                    className="w-7 h-7 flex items-center justify-center border border-[#D8CBA1] hover:border-[#1B3A2B] active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => removeFromCart(product.id)}
                    className="w-7 h-7 flex items-center justify-center text-[#8C2E33] hover:text-[#6B1E2B]"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="border border-[#E4D6A7] bg-[#FBF7EC] p-4 h-fit">
            <h2 className="ff-display text-lg mb-3">Summary</h2>
            <div className="text-sm space-y-1">
              <div className="flex justify-between tabular">
                <span className="text-[#5C5842]">Subtotal</span>
                <span>{money(subtotal)}</span>
              </div>
              {bizUnlockedSavings && (
                <div className="flex justify-between tabular text-[#1B3A2B]">
                  <span>Business savings</span>
                  <span>− {money(savings)}</span>
                </div>
              )}
              <div className="flex items-center gap-1.5 text-xs text-[#5C5842] pt-2">
                <Truck className="w-3.5 h-3.5" />
                {isBusiness
                  ? "Freight quoted at checkout for bulk orders"
                  : "Delivered within 2 days"}
              </div>
            </div>

            <button className="w-full mt-4 py-2.5 bg-[#1B3A2B] text-[#F3ECDD] text-sm hover:bg-[#14140F] active:bg-[#0E1F17] transition-colors">
              Proceed to checkout
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

function ProductDetailPage({
  product,
  allProducts,
  cart,
  isBusiness,
  bizUnlocked,
  onAddToCart,
  onSetQty,
  onBack,
  onOpenProduct,
}) {
  const qtyInCart = cart[product.id] || 0;
  const description = useMemo(() => generateDescription(product), [product]);
  const reviews = useMemo(() => generateReviews(product), [product]);
  const rating = useMemo(() => avgRating(reviews), [reviews]);

  const similar = useMemo(
    () =>
      allProducts
        .filter((p) => p.id !== product.id && p.category === product.category)
        .slice(0, 4),
    [allProducts, product],
  );

  const disc = discountPct(product);
  const showMaxSaver = isBusiness && disc >= MAX_SAVER_THRESHOLD;
  const displayPrice = isBusiness
    ? bizUnlocked
      ? product.bizPrice
      : product.indivPrice
    : product.indivPrice;

  return (
    <main className="max-w-6xl mx-auto px-5 py-10">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[#5C5842] hover:text-[#1B3A2B] transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to catalogue
      </button>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-10">
        {/* Photo */}
        <div className="relative">
          {showMaxSaver && (
            <span className="absolute top-3 right-3 z-10 flex items-center gap-1 bg-[#C9A227] text-[#14140F] text-[11px] px-2 py-0.5">
              <BadgePercent className="w-3 h-3" /> Max Saver
            </span>
          )}
          {product.farmerAdded && (
            <span className="absolute top-3 left-3 z-10 flex items-center gap-1 bg-[#1B3A2B] text-[#F3ECDD] text-[11px] px-2 py-0.5">
              <Sprout className="w-3 h-3" /> New listing
            </span>
          )}
          <ProductPhoto
            product={product}
            className="w-full h-72 sm:h-96 object-cover border border-[#E4D6A7]"
          />
        </div>

        {/* Details */}
        <div>
          <h1 className="ff-display text-3xl sm:text-4xl leading-tight">
            {product.name}
          </h1>
          <div className="flex items-center gap-2 mt-2 text-sm text-[#5C5842]">
            <MapPin className="w-3.5 h-3.5" />
            {product.farmer}
          </div>

          {reviews.length > 0 && (
            <div className="flex items-center gap-2 mt-3">
              <StarRow rating={rating} />
              <span className="text-sm text-[#5C5842] tabular">
                {rating.toFixed(1)} · {reviews.length} review
                {reviews.length !== 1 ? "s" : ""}
              </span>
            </div>
          )}

          <div className="mt-5 flex items-baseline gap-1.5">
            <span className="ff-display text-3xl tabular text-[#1B3A2B]">
              {money(displayPrice)}
            </span>
            <span className="text-sm text-[#5C5842]">/ {product.unit}</span>
            {isBusiness && bizUnlocked && (
              <span className="text-sm text-[#8A6D1E] line-through tabular ml-1">
                {money(product.indivPrice)}
              </span>
            )}
          </div>

          {isBusiness ? (
            <p className="text-xs text-[#8A6D1E] mt-1">
              {bizUnlocked
                ? `Bulk only — min ${product.minBulkQty} ${product.unit}`
                : "Verify GSTIN to see business rate"}
            </p>
          ) : (
            <p className="text-xs text-[#8A6D1E] mt-1">
              Business rate: {money(product.bizPrice)}/{product.unit} — min{" "}
              {product.minBulkQty} {product.unit}
            </p>
          )}

          <p className="text-sm text-[#5C5842] leading-relaxed mt-5">
            {description}
          </p>

          <div className="mt-6 max-w-xs">
            {qtyInCart > 0 ? (
              <div className="flex items-center justify-between border border-[#D8CBA1] px-2 py-1.5">
                <button
                  onClick={() =>
                    onSetQty(product, qtyInCart - (isBusiness ? 5 : 1))
                  }
                  className="w-7 h-7 flex items-center justify-center active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                >
                  <Minus className="w-3.5 h-3.5" />
                </button>
                <span className="text-sm tabular">
                  {qtyInCart} {product.unit}
                </span>
                <button
                  onClick={() =>
                    onSetQty(product, qtyInCart + (isBusiness ? 5 : 1))
                  }
                  className="w-7 h-7 flex items-center justify-center active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => onAddToCart(product)}
                className="w-full py-2.5 text-sm border border-[#1B3A2B] text-[#1B3A2B] hover:bg-[#1B3A2B] hover:text-[#F3ECDD] active:bg-[#0E1F17] active:border-[#0E1F17] transition-colors"
              >
                {isBusiness ? "Add bulk order" : "Add to cart"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Reviews */}
      <section className="mt-14 max-w-3xl">
        <div className="flex items-center gap-2 mb-5">
          <MessageSquare className="w-4 h-4 text-[#1B3A2B]" />
          <h2 className="ff-display text-2xl">Reviews</h2>
        </div>
        {reviews.length === 0 ? (
          <p className="text-sm text-[#5C5842]">No reviews yet.</p>
        ) : (
          <div className="space-y-4">
            {reviews.map((r) => (
              <div
                key={r.id}
                className="border border-[#E4D6A7] bg-[#FBF7EC] p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{r.name}</span>
                  <span className="text-xs text-[#8A8468]">
                    {timeAgo(r.daysAgo)}
                  </span>
                </div>
                <div className="mt-1.5">
                  <StarRow rating={r.rating} />
                </div>
                <p className="text-sm text-[#5C5842] leading-relaxed mt-2">
                  {r.text}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Similar products */}
      {similar.length > 0 && (
        <section className="mt-14">
          <h2 className="ff-display text-2xl mb-5">You may also like</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {similar.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                isBusiness={isBusiness}
                bizUnlocked={bizUnlocked}
                qtyInCart={cart[p.id] || 0}
                onAdd={() => onAddToCart(p)}
                onSetQty={(q) => onSetQty(p, q)}
                onOpen={() => onOpenProduct(p)}
              />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

function CartButton({ count, onClick, active }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`relative flex items-center gap-2 px-4 py-2 text-sm border border-[#C9A227] transition-colors ${
        active
          ? "bg-[#C9A227] text-[#14140F]"
          : "text-[#F3ECDD] hover:bg-[#C9A227] hover:text-[#14140F]"
      }`}
    >
      <ShoppingCart className="w-4 h-4" />
      Cart
      {count > 0 && (
        <span className="absolute -top-2 -right-2 min-w-4.5 h-4.5 px-1 flex items-center justify-center rounded-full bg-[#C9A227] text-[#14140F] text-[10px] font-semibold">
          {count}
        </span>
      )}
    </button>
  );
}

function ConsumerToggle({ consumerType, onChange }) {
  const household = consumerType === "individual";
  const business = consumerType === "business";
  return (
    <div className="inline-flex border border-[#4A4630] w-full sm:w-auto">
      <button
        onClick={() => onChange("individual")}
        aria-pressed={household}
        className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 text-sm transition-colors ${
          household
            ? "bg-[#C9A227] text-[#14140F] shadow-[inset_0_0_0_1px_#F3ECDD]"
            : "bg-transparent text-[#C9C3AE] hover:bg-[#1D1C14]"
        }`}
      >
        <User className="w-3.5 h-3.5" /> Household
      </button>
      <button
        onClick={() => onChange("business")}
        aria-pressed={business}
        className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 text-sm transition-colors border-l border-[#4A4630] ${
          business
            ? "bg-[#1B3A2B] text-[#F3ECDD] shadow-[inset_0_0_0_1px_#C9A227]"
            : "bg-transparent text-[#C9C3AE] hover:bg-[#1D1C14]"
        }`}
      >
        <Building2 className="w-3.5 h-3.5" /> Business
      </button>
    </div>
  );
}

function ProductCard({
  product,
  isBusiness,
  bizUnlocked,
  qtyInCart,
  onAdd,
  onSetQty,
  onOpen,
}) {
  const disc = discountPct(product);
  const showMaxSaver = isBusiness && disc >= MAX_SAVER_THRESHOLD;
  const displayPrice = isBusiness
    ? bizUnlocked
      ? product.bizPrice
      : product.indivPrice
    : product.indivPrice;

  function handleCardKeyDown(e) {
    if (onOpen && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      onOpen();
    }
  }

  return (
    <div
      onClick={onOpen}
      onKeyDown={handleCardKeyDown}
      role={onOpen ? "button" : undefined}
      tabIndex={onOpen ? 0 : undefined}
      className={`border border-[#E4D6A7] bg-[#FBF7EC] flex flex-col relative overflow-hidden ${
        onOpen ? "cursor-pointer hover:border-[#1B3A2B] transition-colors" : ""
      }`}
    >
      {showMaxSaver && (
        <span className="absolute top-3 right-3 z-10 flex items-center gap-1 bg-[#C9A227] text-[#14140F] text-[11px] px-2 py-0.5">
          <BadgePercent className="w-3 h-3" /> Max Saver
        </span>
      )}
      {product.farmerAdded && (
        <span className="absolute top-3 left-3 z-10 flex items-center gap-1 bg-[#1B3A2B] text-[#F3ECDD] text-[11px] px-2 py-0.5">
          <Sprout className="w-3 h-3" /> New listing
        </span>
      )}
      <ProductPhoto product={product} className="w-full h-40 object-cover" />

      <div className="p-4 flex flex-col flex-1">
        <h3 className="ff-display text-lg leading-snug">{product.name}</h3>
        <p className="text-xs text-[#5C5842] mt-0.5">{product.farmer}</p>

        <div className="mt-3 flex items-baseline gap-1.5">
          <span className="ff-display text-2xl tabular text-[#1B3A2B]">
            {money(displayPrice)}
          </span>
          <span className="text-xs text-[#5C5842]">/ {product.unit}</span>
          {isBusiness && bizUnlocked && (
            <span className="text-xs text-[#8A6D1E] line-through tabular ml-1">
              {money(product.indivPrice)}
            </span>
          )}
        </div>

        {isBusiness ? (
          <p className="text-[11px] text-[#8A6D1E] mt-1">
            {bizUnlocked
              ? `Bulk only — min ${product.minBulkQty} ${product.unit}`
              : "Verify GSTIN to see business rate"}
          </p>
        ) : (
          <p className="text-[11px] text-[#8A6D1E] mt-1">
            Business rate: {money(product.bizPrice)}/{product.unit} — min{" "}
            {product.minBulkQty} {product.unit}
          </p>
        )}

        <div className="mt-auto pt-4">
          {qtyInCart > 0 ? (
            <div
              onClick={(e) => e.stopPropagation()}
              className="flex items-center justify-between border border-[#D8CBA1] px-2 py-1.5"
            >
              <button
                onClick={() => onSetQty(qtyInCart - (isBusiness ? 5 : 1))}
                className="w-6 h-6 flex items-center justify-center active:bg-[#1B3A2B] active:text-[#F3ECDD]"
              >
                <Minus className="w-3.5 h-3.5" />
              </button>
              <span className="text-sm tabular">
                {qtyInCart} {product.unit}
              </span>
              <button
                onClick={() => onSetQty(qtyInCart + (isBusiness ? 5 : 1))}
                className="w-6 h-6 flex items-center justify-center active:bg-[#1B3A2B] active:text-[#F3ECDD]"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAdd();
              }}
              className="w-full py-2 text-sm border border-[#1B3A2B] text-[#1B3A2B] hover:bg-[#1B3A2B] hover:text-[#F3ECDD] active:bg-[#0E1F17] active:border-[#0E1F17] transition-colors"
            >
              {isBusiness ? "Add bulk order" : "Add to cart"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
