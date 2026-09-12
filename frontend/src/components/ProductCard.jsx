import React from "react";
import { BadgePercent, Sprout, Plus, Minus } from "lucide-react";
import { discountPct, money, MAX_SAVER_THRESHOLD } from "../utils/marketplace.js";
import ProductPhoto from "./ProductPhoto.jsx";
import axios from 'axios';
import { LiquidButton } from "./ui/liquid-glass-button";


export default function ProductCard({
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
              className="flex items-center justify-between gap-2"
            >
              <LiquidButton
                icon={<Minus className="w-3.5 h-3.5" />}
                onClick={() => onSetQty(qtyInCart - (isBusiness ? 5 : 1))}
                size="xs"
                decor={false}
                className="w-8 h-8 px-0"
              />
              <span className="text-sm tabular flex-1 text-center">
                {qtyInCart} {product.unit}
              </span>
              <LiquidButton
                icon={<Plus className="w-3.5 h-3.5" />}
                onClick={() => onSetQty(qtyInCart + (isBusiness ? 5 : 1))}
                size="xs"
                decor={false}
                className="w-8 h-8 px-0"
              />
            </div>
          ) : (
            <LiquidButton
              label={isBusiness ? "Add bulk order" : "Add to cart"}
              onClick={(e) => {
                e.stopPropagation();
                onAdd();
              }}
              className="w-full"
            />
          )}
        </div>
      </div>
    </div>
  );
}
