import React from "react";
import { Star } from "lucide-react";

export default function StarRow({ rating, size = "w-3.5 h-3.5" }) {
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
