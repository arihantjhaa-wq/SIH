// frontend/src/pages/DeveloperDashboard.jsx
//
// "Management dashboard" for the developer/admin role. Shows ALL farmers'
// products irrespective of owner. Authorized server-side: GET /products/admin
// is guarded by verifyJWT + isDeveloper; the frontend never trusts a param.
//
// Visually aligned with the Kheti Seedha design system: dark header
// #14140F, warm off-white #F3ECDD, gold #C9A227, Fraunces headings.
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Leaf, ArrowLeft, RefreshCcw, Trash2, X } from "lucide-react";
import { money } from "../utils/marketplace.js";
import { getAdminProducts, deleteProduct } from "../services/productService.js";
import ProductPhoto from "../components/ProductPhoto.jsx";
import ProfileButton from "../components/ProfileButton.jsx";
import DancingLetters from "../components/ui/dancing-letters";
import { LiquidButton } from "../components/ui/liquid-glass-button";

function StatCard({ value, label }) {
  return (
    <div className="flex-1 flex flex-col justify-center items-center gap-1 border border-[#E4D6A7] bg-white py-5">
      <span className="ff-display text-2xl tabular text-[#14140F]">{value}</span>
      <span className="text-xs uppercase tracking-wide text-[#5C5842]">{label}</span>
    </div>
  );
}

export default function DeveloperDashboard({ onSwitch, onLogout, user }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [toast, setToast] = useState(null);

  function flashToast(msg) {
    setToast(msg);
    window.clearTimeout(flashToast._t);
    flashToast._t = window.setTimeout(() => setToast(null), 2200);
  }

  const fetchAdminProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await getAdminProducts();
      setProducts(list);
    } catch (err) {
      const msg = err?.response?.data?.message || err?.message || "Could not load products";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAdminProducts();
  }, [fetchAdminProducts]);

  const stats = useMemo(() => {
    const farmers = new Set(products.map((p) => p.farmer).filter(Boolean)).size;
    const farmerListings = products.filter((p) => p.farmerAdded).length;
    const seed = products.length - farmerListings;
    return {
      total: products.length,
      farmers,
      farmerListings,
      seed,
    };
  }, [products]);

  // Keep products sorted by creation order (API returns createdAt asc)
  const sorted = products;

  async function handleDelete(id, name) {
    setDeletingId(id);
    try {
      await deleteProduct(id);
      setProducts((prev) => prev.filter((p) => (p._id || p.id) !== id));
      flashToast(`${name} deleted`);
    } catch (err) {
      const msg = err?.response?.data?.message || err?.message || "Could not delete product";
      flashToast(msg);
    } finally {
      setDeletingId(null);
    }
  }

  // Display owner of a product — populated via /admin populate(addedBy) when
  // available, otherwise fall back to the legacy `farmer` string field.
  function ownerLabel(product) {
    if (product.addedBy && typeof product.addedBy === "object") {
      const o = product.addedBy;
      return o.fullName || o.username || o.email || product.farmer || "—";
    }
    if (product.farmer) return product.farmer;
    if (product.addedBy) return String(product.addedBy);
    return "Seed / demo catalogue";
  }

  const ownerEmail = (product) => {
    // Only owner-linked products (addedBy populated) show an email.
    if (product.addedBy && typeof product.addedBy === "object") {
      return product.addedBy.email || null;
    }
    return null;
  };

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
      {/* Header */}
      {/* ---------------------------------------------------------------- */}
      <div className="bg-[#14140F] text-[#F3ECDD]">
        <header className="border-b border-[#33301F]">
          <div className="max-w-6xl mx-auto px-5 py-5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Leaf className="w-6 h-6 text-[#E5A93C]" strokeWidth={1.75} />
              <span className="brand-logo">
                <DancingLetters
                  text="कृषि Setu"
                  className="inline-flex items-center"
                  getLetterColorClass={(grapheme) =>
                    /\p{Script=Devanagari}/u.test(grapheme)
                      ? "ff-gotu text-[#E5A93C] tracking-[0.01em]"
                      : "ff-gotu text-[#F4D06F] tracking-[0.04em]"
                  }
                />
              </span>
              <span className="ml-2 text-[11px] uppercase tracking-wide border border-[#C9A227] text-[#C9A227] px-2 py-0.5">
                Developer • Management dashboard
              </span>
            </div>
            <div className="flex items-center gap-3">
              <ProfileButton user={user} onSwitch={onSwitch} onLogout={onLogout} />
            </div>
          </div>
        </header>

        <section className="max-w-6xl mx-auto px-5 pt-10 pb-8">
          <h1 className="ff-display text-3xl sm:text-4xl leading-[1.1] max-w-2xl">
            All marketplace products
          </h1>
          <p className="mt-3 text-[15px] text-[#C9C3AE] max-w-2xl">
            Every listing across every farmer is here — seed catalogue plus every
            farmer's own. Deleting here removes the listing for everyone.
          </p>
        </section>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Stats + refresh */}
      {/* ---------------------------------------------------------------- */}
      <div className="max-w-6xl mx-auto px-5 pt-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <StatCard value={loading ? "—" : String(stats.total)} label="Total listings" />
          <StatCard value={loading ? "—" : String(stats.seed)} label="Seed catalogue" />
          <StatCard value={loading ? "—" : String(stats.farmerListings)} label="Farmer listings" />
          <StatCard value={loading ? "—" : String(stats.farmers)} label="Distinct farmer names" />
        </div>

        <div className="mt-6 flex items-center justify-between gap-3">
          <h2 className="ff-display text-xl">Inventory</h2>
          <LiquidButton
            label="Refresh"
            icon={<RefreshCcw className="w-3.5 h-3.5" />}
            onClick={fetchAdminProducts}
            disabled={loading}
            aria-label="Refresh"
            size="sm"
            decor={false}
            className="bg-transparent text-[#5C5842] hover:text-[#1B3A2B] hover:bg-transparent"
          />
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Error / loading / empty */}
      {/* ---------------------------------------------------------------- */}
      <div className="max-w-6xl mx-auto px-5 mt-4 pb-8">
        {loading && (
          <p className="border border-dashed border-[#D8CBA1] bg-[#FBF7EC] py-10 text-center text-sm text-[#5C5842]">
            Loading all products…
          </p>
        )}

        {!loading && error && (
          <div
            role="alert"
            className="border border-[#E08B83] bg-[#FBEAE8] text-[#7A2A22] px-4 py-3 text-sm"
          >
            {error}
          </div>
        )}

        {!loading && !error && sorted.length === 0 && (
          <p className="border border-dashed border-[#D8CBA1] bg-[#FBF7EC] py-10 text-center text-sm text-[#5C5842]">
            Empty — seed the catalogue from the Marketplace Backend to get started.
          </p>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Inventory table (desktop) / cards (mobile) */}
        {/* ---------------------------------------------------------------- */}
        {!loading && !error && sorted.length > 0 && (
          <>
            {/* Desktop table */}
            <div className="hidden lg:block border border-[#E4D6A7] bg-white overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#FBF7EC] text-[#5C5842] text-xs uppercase tracking-wide">
                    <th className="text-left font-medium px-4 py-3">Product</th>
                    <th className="text-left font-medium px-4 py-3">Category</th>
                    <th className="text-left font-medium px-4 py-3">Owner</th>
                    <th className="text-left font-medium px-4 py-3">Household</th>
                    <th className="text-left font-medium px-4 py-3">Bulk</th>
                    <th className="text-left font-medium px-4 py-3">Min bulk</th>
                    <th className="text-left font-medium px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0E6C5]">
                  {sorted.map((p) => (
                    <tr key={p._id || p.id} className="align-top">
                      <td className="px-4 py-3">
                        <span className="ff-display text-sm text-[#14140F]">{p.name}</span>
                        <span className="block text-xs text-[#5C5842]">
                          {p.farmerAdded ? "Farmer listing" : "Seed catalogue"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-[#5C5842]">{p.category} · {p.unit}</td>
                      <td className="px-4 py-3 text-xs tabular text-[#2A2820]">
                        {ownerLabel(p)}
                        {ownerEmail(p) && (
                          <span className="block text-[11px] text-[#8A8468]">{ownerEmail(p)}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 tabular text-sm text-[#1B3A2B]">{money(p.indivPrice)}</td>
                      <td className="px-4 py-3 tabular text-xs text-[#8A6D1E]">{money(p.bizPrice)}</td>
                      <td className="px-4 py-3 tabular text-xs text-[#5C5842]">
                        {p.minBulkQty} {p.unit}
                      </td>
                      <td className="px-4 py-3">
                        <LiquidButton
                          label={deletingId === (p._id || p.id) ? "Deleting…" : "Delete"}
                          icon={<Trash2 className="w-3.5 h-3.5" />}
                          onClick={() => handleDelete(p._id || p.id, p.name)}
                          disabled={!!deletingId}
                          aria-label={`Delete ${p.name}`}
                          size="xs"
                          decor={false}
                          className="bg-transparent text-[#8C2E33] hover:text-[#6B1E2B] hover:bg-transparent"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Card grid (mobile / tablet) */}
            <div className="grid lg:hidden grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              {sorted.map((p) => (
                <div key={p._id || p.id} className="border border-[#E4D6A7] bg-[#FBF7EC] flex flex-col">
                  <ProductPhoto product={p} className="w-full h-32 object-cover" />
                  <div className="p-3 flex-1 flex flex-col">
                    <h3 className="ff-display text-base leading-snug">{p.name}</h3>
                    <p className="text-[11px] text-[#5C5842]">{p.category} · {p.unit}</p>
                    <p className="text-[11px] text-[#8A8468] mt-1">Owner: {ownerLabel(p)}</p>
                    {ownerEmail(p) && (
                      <p className="text-[11px] text-[#8A8468]">{ownerEmail(p)}</p>
                    )}
                    <p className="text-sm tabular mt-1 text-[#1B3A2B]">
                      {money(p.indivPrice)} <span className="text-[#5C5842]">household</span>
                    </p>
                    <p className="text-xs tabular text-[#8A6D1E]">
                      {money(p.bizPrice)} bulk · min {p.minBulkQty} {p.unit}
                    </p>
                    <span className="text-[11px] mt-1 text-[#5C5842]">
                      {p.farmerAdded ? "Farmer listing" : "Seed catalogue"}
                    </span>
                    <LiquidButton
                      label={deletingId === (p._id || p.id) ? "Deleting…" : "Remove listing"}
                      icon={<Trash2 className="w-3.5 h-3.5" />}
                      onClick={() => handleDelete(p._id || p.id, p.name)}
                      disabled={!!deletingId}
                      size="xs"
                      decor={false}
                      className="mt-auto bg-transparent text-[#8C2E33] hover:text-[#6B1E2B] hover:bg-transparent"
                    />
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {toast && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 bg-[#14140F] text-[#F3ECDD] text-sm px-4 py-2.5 flex items-center gap-2 shadow-lg border border-[#C9A227]/40 z-50">
          {toast}
          <LiquidButton
            icon={<X className="w-3.5 h-3.5" />}
            onClick={() => setToast(null)}
            aria-label="Dismiss"
            size="xs"
            decor={false}
            className="ml-2 w-6 h-6 px-0 bg-[#2A2825] hover:bg-[#3A382F]"
          />
        </div>
      )}
    </div>
  );
}
