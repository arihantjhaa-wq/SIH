# Kheti Seedha

A farm-to-door marketplace: farmers list produce, households buy at fair prices,
and registered businesses unlock bulk rates with a valid GSTIN.

## Setup

```bash
npm install
npm run dev
```

Then open the printed local URL (usually http://localhost:5173).

## Build for production

```bash
npm run build
npm run preview
```

## Structure

- `src/App.jsx` — mounts the marketplace
- `src/FarmMarketplace.jsx` — the whole app: role picker, farmer portal, consumer marketplace, cart
- `src/index.css` — Tailwind entry point (Tailwind v4, loaded via `@tailwindcss/vite`)
- `src/main.jsx` — React root

## Notes

- Product photos are pulled by keyword from a free, key-less photo service at runtime — an
  internet connection is needed to see images, and you can swap in your own image URLs/CDN later.
- Farmer-published listings live in React state only (no backend), so they reset on page reload.
