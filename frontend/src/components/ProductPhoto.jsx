import React, { useState } from "react";
import { ImageOff } from "lucide-react";
import { photoUrl } from "../utils/marketplace.js";

export default function ProductPhoto({ product, className }) {
  const [failed, setFailed] = useState(false);
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
