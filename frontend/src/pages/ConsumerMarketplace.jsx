import React, { useState, useMemo } from "react";
import {
  Leaf,
  ArrowLeft,
  Lock,
  CircleCheck as CheckCircle2,
  BadgePercent,
  Search,
  X,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  discountPct,
  isGstinValid,
  money,
  MAX_SAVER_THRESHOLD,
} from "../utils/marketplace.js";
import { useProducts } from "../context/ProductContext.jsx";
import { useCart } from "../context/CartContext.jsx";
import { usePersistentState } from "../hooks/usePersistentState.js";
import { useAuth } from "../context/AuthContext.jsx";
import { verifyGstinApi } from "../services/gstService.js";
import CartButton from "../components/CartButton.jsx";
import ConsumerToggle from "../components/ConsumerToggle.jsx";
import ProductCard from "../components/ProductCard.jsx";
import CartPage from "./CartPage.jsx";
import ProductDetailPage from "./ProductDetailPage.jsx";

export default function ConsumerMarketplace({ onSwitch, onLogout }) {
  const { products: allProducts, loading, error } = useProducts();
  const { cart, addToCart, setQty: setCartQty, removeFromCart } = useCart();
  const { user } = useAuth();

  const [consumerType, setConsumerType] = usePersistentState(
    "ks_consumerType",
    "individual",
  );
  const [gstin, setGstin] = usePersistentState("ks_gstin", "");
  const [gstinTouched, setGstinTouched] = useState(false);
  const [gstVerificationStatus, setGstVerificationStatus] = useState(null);
  const [gstVerificationData, setGstVerificationData] = useState(null);
  const [gstVerifying, setGstVerifying] = useState(false);
  const [category, setCategory] = usePersistentState("ks_category", "All");
  const [search, setSearch] = useState("");
  const [maxSaverOnly, setMaxSaverOnly] = usePersistentState(
    "ks_maxSaverOnly",
    false,
  );
  const [view, setView] = useState("shop");
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [toast, setToast] = useState(null);

  const isBusiness = consumerType === "business";
  const isDeveloper = user?.isDeveloper || user?.username === "__developer__";

  // Business is unlocked only when GST verification returns VERIFIED status
  const bizUnlocked = isBusiness && gstVerificationStatus === "VERIFIED";

  const categories = useMemo(
    () => ["All", ...Array.from(new Set(allProducts.map((p) => p.category)))],
    [allProducts],
  );

  const searchQuery = search.trim().toLowerCase();

  function matchesQuery(p, q) {
    return (
      p.name.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q) ||
      p.farmer.toLowerCase().includes(q)
    );
  }

  const directSearchMatches = useMemo(() => {
    if (!searchQuery) return null;
    return allProducts.filter((p) => matchesQuery(p, searchQuery));
  }, [allProducts, searchQuery]);

  const relatedSearchMatches = useMemo(() => {
    if (!searchQuery || (directSearchMatches && directSearchMatches.length))
      return [];
    const words = searchQuery.split(/\s+/).filter((w) => w.length > 2);
    if (words.length === 0) return [];
    const scored = allProducts
      .map((p) => {
        const haystack = `${p.name} ${p.category} ${p.farmer}`.toLowerCase();
        const score = words.reduce(
          (s, w) => s + (haystack.includes(w) ? 1 : 0),
          0,
        );
        return { p, score };
      })
      .filter((s) => s.score > 0)
      .sort((a, b) => b.score - a.score);
    return scored.slice(0, 8).map((s) => s.p);
  }, [allProducts, searchQuery, directSearchMatches]);

  const isRelatedFallback =
    !!searchQuery && (!directSearchMatches || directSearchMatches.length === 0);

  const visibleProducts = useMemo(() => {
    let list = allProducts;
    if (category !== "All") list = list.filter((p) => p.category === category);
    if (isBusiness && maxSaverOnly)
      list = list.filter((p) => discountPct(p) >= MAX_SAVER_THRESHOLD);
    if (searchQuery) {
      list = isRelatedFallback
        ? list.filter((p) => relatedSearchMatches.some((r) => r.id === p.id))
        : list.filter((p) => matchesQuery(p, searchQuery));
    }
    return list;
  }, [
    allProducts,
    category,
    isBusiness,
    maxSaverOnly,
    searchQuery,
    isRelatedFallback,
    relatedSearchMatches,
  ]);

  function flashToast(msg) {
    setToast(msg);
    window.clearTimeout(flashToast._t);
    flashToast._t = window.setTimeout(() => setToast(null), 2200);
  }

  async function handleVerifyGstin() {
    if (!gstin || gstin.length !== 15) {
      setGstVerificationStatus("FORMAT_INVALID");
      setGstVerificationData(null);
      return;
    }

    setGstVerifying(true);
    setGstVerificationStatus(null);
    setGstVerificationData(null);

    try {
      const result = await verifyGstinApi({ gstin });
      setGstVerificationStatus(result.status);
      setGstVerificationData(result.data || null);

      if (result.status === "VERIFIED") {
        flashToast(
          result.data?.isDemo
            ? "Developer demo GSTIN verified"
            : "GSTIN verified successfully"
        );
      }
    } catch (err) {
      setGstVerificationStatus("PROVIDER_UNAVAILABLE");
      setGstVerificationData(null);
      flashToast("Could not verify GSTIN. Please try again.");
    } finally {
      setGstVerifying(false);
    }
  }

  async function handleUseDeveloperDemo() {
    setGstin("07AAAAA0000A1Z5");
    setGstVerifying(true);
    setGstVerificationStatus(null);
    setGstVerificationData(null);

    try {
      const result = await verifyGstinApi({
        gstin: "07AAAAA0000A1Z5",
        isDemoRequest: true,
      });
      setGstVerificationStatus(result.status);
      setGstVerificationData(result.data || null);
      flashToast("Developer demo GSTIN activated");
    } catch (err) {
      flashToast("Could not activate developer demo");
    } finally {
      setGstVerifying(false);
    }
  }

  function handleGstinChange(value) {
    setGstin(value.toUpperCase());
    // Reset verification when GSTIN changes
    if (gstVerificationStatus) {
      setGstVerificationStatus(null);
      setGstVerificationData(null);
    }
  }

  function addToCartHandler(product) {
    if (isBusiness && !bizUnlocked) {
      flashToast("Add a valid GSTIN to unlock business pricing");
      return;
    }
    const startQty = isBusiness ? product.minBulkQty : 1;
    addToCart(product.id, startQty);
    flashToast(
      isBusiness
        ? `${product.name} bulk order added`
        : `${product.name} added to your order`,
    );
  }

  function setQtyHandler(product, qty) {
    const floor = isBusiness ? product.minBulkQty : 1;
    const clean = Math.max(0, qty);
    if (clean <= 0) {
      removeFromCart(product.id);
    } else {
      setCartQty(product.id, clean < floor ? floor : clean);
    }
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
              {onLogout && (
                <button
                  onClick={onLogout}
                  className="px-2 py-2 text-sm text-[#C9C3AE] hover:text-[#C9A227] transition-colors"
                >
                  Log out
                </button>
              )}
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
            {onLogout && (
              <button
                onClick={onLogout}
                className="px-2 py-2 text-xs text-[#C9C3AE] hover:text-[#C9A227]"
              >
                Log out
              </button>
            )}
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
                    onChange={(e) => handleGstinChange(e.target.value)}
                    onBlur={() => setGstinTouched(true)}
                    placeholder="27AAACW7823G1ZV"
                    maxLength={15}
                    className="flex-1 border border-[#4A4630] bg-[#14140F] text-[#F3ECDD] px-3 py-2 text-sm tracking-wide outline-none focus:border-[#C9A227]"
                    disabled={gstVerifying}
                  />
                  <button
                    onClick={handleVerifyGstin}
                    disabled={gstVerifying || !gstin || gstin.length !== 15}
                    className="px-4 py-2 bg-[#C9A227] text-[#14140F] text-sm font-medium hover:bg-[#D4AE3D] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {gstVerifying ? "Verifying..." : "Verify"}
                  </button>
                </div>

                {/* Verification Status Messages */}
                {gstVerifying && (
                  <div className="mt-2 flex items-center gap-2 text-xs text-[#C9A227]">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Verifying with GST portal...
                  </div>
                )}

                {gstVerificationStatus === "VERIFIED" && gstVerificationData && (
                  <div className="mt-3 p-3 border border-[#4A8F5A] bg-[#1B3A2B]/20">
                    <div className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-[#6FC282] mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-[#6FC282] font-medium">
                          GSTIN Verified
                          {gstVerificationData.isDemo && (
                            <span className="ml-2 text-xs text-[#C9A227]">(Developer Demo)</span>
                          )}
                        </p>
                        <p className="text-xs text-[#C9C3AE] mt-1">
                          <strong>{gstVerificationData.legalName}</strong>
                        </p>
                        {gstVerificationData.tradeName && gstVerificationData.tradeName !== gstVerificationData.legalName && (
                          <p className="text-xs text-[#8A8468] mt-0.5">
                            Trading as: {gstVerificationData.tradeName}
                          </p>
                        )}
                        <p className="text-xs text-[#8A8468] mt-0.5">
                          Status: {gstVerificationData.gstinStatus} • {gstVerificationData.taxpayerType}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {gstVerificationStatus === "NOT_VERIFIED" && (
                  <div className="mt-2 flex items-start gap-2 p-2 border border-[#C4544A]/40 bg-[#C4544A]/10">
                    <AlertCircle className="w-4 h-4 text-[#C4544A] mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-[#C4544A]">
                      GSTIN not found or inactive with tax authority.
                    </p>
                  </div>
                )}

                {gstVerificationStatus === "FORMAT_INVALID" && (
                  <div className="mt-2 flex items-start gap-2 p-2 border border-[#C4544A]/40 bg-[#C4544A]/10">
                    <AlertCircle className="w-4 h-4 text-[#C4544A] mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-[#C4544A]">
                      Invalid GSTIN format. Must be 15 alphanumeric characters (e.g. 27AAACW7823G1ZV).
                    </p>
                  </div>
                )}

                {gstVerificationStatus === "PROVIDER_UNAVAILABLE" && (
                  <div className="mt-2 p-2 border border-[#C9A227]/40 bg-[#C9A227]/10">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-[#C9A227] mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-xs text-[#C9A227]">
                          GST verification service is temporarily unavailable.
                        </p>
                        <button
                          onClick={handleVerifyGstin}
                          className="mt-1 text-xs text-[#C9A227] underline hover:text-[#D4AE3D]"
                        >
                          Retry verification
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {gstVerificationStatus === "VERIFICATION_DISABLED" && (
                  <div className="mt-2 p-2 border border-[#8A8468]/40 bg-[#8A8468]/10">
                    <p className="text-xs text-[#8A8468]">
                      GST verification is currently disabled.
                    </p>
                  </div>
                )}

                {/* Developer Demo Button */}
                {isDeveloper && (
                  <div className="mt-3 pt-3 border-t border-[#33301F]">
                    <button
                      onClick={handleUseDeveloperDemo}
                      disabled={gstVerifying}
                      className="w-full px-3 py-2 text-xs border border-[#8A8468] text-[#8A8468] hover:border-[#C9A227] hover:text-[#C9A227] transition-colors disabled:opacity-40"
                    >
                      Use Developer Demo GSTIN
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </div>

      {view === "shop" && (
        <div className="sticky top-0 z-10 bg-[#F3ECDD]/95 backdrop-blur border-y border-[#E4D6A7]">
          <section className="max-w-6xl mx-auto px-5 pt-3">
            <div className="relative">
              <Search className="w-4 h-4 text-[#8A8468] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                type="search"
                placeholder="Search products, categories or farmers…"
                className="w-full border border-[#D8CBA1] bg-white pl-9 pr-9 py-2 text-sm outline-none focus:border-[#1B3A2B] placeholder:text-[#8A8468]"
              />
              {search && (
                <button
                  onClick={() => setSearch("")}
                  aria-label="Clear search"
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8A8468] hover:text-[#1B3A2B]"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </section>

          <section className="max-w-6xl mx-auto px-5 py-3 flex flex-wrap items-center gap-2">
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
                  !bizUnlocked
                    ? "Verify your GSTIN to use Max Saver"
                    : undefined
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
        </div>
      )}

      {view === "shop" && (
        <main className="max-w-6xl mx-auto px-5 py-8">
          {loading && (
            <p className="text-sm text-[#5C5842] py-10 text-center">
              Loading products…
            </p>
          )}
          {error && (
            <p className="text-sm text-[#C4544A] py-10 text-center">{error}</p>
          )}
          {!loading && !error && searchQuery && (
            <p className="text-sm text-[#5C5842] mb-4">
              {isRelatedFallback ? (
                visibleProducts.length > 0 ? (
                  <>
                    No exact matches for "{search}" — showing{" "}
                    <span className="text-[#1B3A2B]">related products</span>{" "}
                    instead.
                  </>
                ) : (
                  <>No products found for "{search}".</>
                )
              ) : (
                <>
                  {visibleProducts.length} result
                  {visibleProducts.length !== 1 ? "s" : ""} for "{search}"
                </>
              )}
            </p>
          )}
          {!loading && !error && (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {visibleProducts.map((p) => (
                <ProductCard
                  key={p.id}
                  product={p}
                  isBusiness={isBusiness}
                  bizUnlocked={bizUnlocked}
                  qtyInCart={cart[p.id] || 0}
                  onAdd={() => addToCartHandler(p)}
                  onSetQty={(q) => setQtyHandler(p, q)}
                  onOpen={() => openProduct(p)}
                />
              ))}
              {visibleProducts.length === 0 && !searchQuery && (
                <p className="col-span-full text-sm text-[#5C5842] py-10 text-center">
                  No products match this filter yet.
                </p>
              )}
            </div>
          )}
        </main>
      )}

      {view === "cart" && (
        <CartPage
          cartLines={cartLines}
          isBusiness={isBusiness}
          bizUnlocked={bizUnlocked}
          priceFor={priceFor}
          subtotal={subtotal}
          savings={savings}
          bizUnlockedSavings={bizUnlocked && savings > 0}
          setQty={setQtyHandler}
          removeFromCart={removeFromCart}
          onBack={() => setView("shop")}
        />
      )}

      {view === "product" && selectedProduct && (
        <ProductDetailPage
          product={selectedProduct}
          allProducts={allProducts}
          cart={cart}
          isBusiness={isBusiness}
          bizUnlocked={bizUnlocked}
          onAddToCart={addToCartHandler}
          onSetQty={setQtyHandler}
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
