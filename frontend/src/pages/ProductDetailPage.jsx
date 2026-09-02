import React, { useMemo } from "react";
import { ArrowLeft, BadgePercent, Sprout, MapPin, MessageSquare, Plus, Minus } from "lucide-react";
import { discountPct, money, MAX_SAVER_THRESHOLD } from "../utils/marketplace.js";
import { generateDescription, generateReviews, avgRating, timeAgo } from "../utils/productContent.js";
import ProductPhoto from "../components/ProductPhoto.jsx";
import StarRow from "../components/StarRow.jsx";
import ProductCard from "../components/ProductCard.jsx";

export default function ProductDetailPage({
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
                  onClick={() => onSetQty(product, qtyInCart - (isBusiness ? 5 : 1))}
                  className="w-7 h-7 flex items-center justify-center active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                >
                  <Minus className="w-3.5 h-3.5" />
                </button>
                <span className="text-sm tabular">
                  {qtyInCart} {product.unit}
                </span>
                <button
                  onClick={() => onSetQty(product, qtyInCart + (isBusiness ? 5 : 1))}
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
              <div key={r.id} className="border border-[#E4D6A7] bg-[#FBF7EC] p-4">
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
