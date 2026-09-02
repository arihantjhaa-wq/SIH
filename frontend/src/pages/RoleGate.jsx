import React from "react";
import { Leaf, Sprout, Store } from "lucide-react";

export default function RoleGate({ onSelect }) {
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
