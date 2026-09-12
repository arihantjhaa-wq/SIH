import React from "react";
import { Leaf, Sprout, Store } from "lucide-react";
import { motion } from "framer-motion";
import DancingLetters from "../components/ui/dancing-letters";
import { LiquidButton } from "../components/ui/liquid-glass-button";

export default function RoleGate({ onSelect, onLogout }) {
  return (
    <div
      className="min-h-screen w-full bg-[#14140F] text-[#F3ECDD] flex flex-col items-center px-5"
      style={{
        fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Gotu:wght@400&family=Work+Sans:wght@400;500;600&display=swap');
        .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
        .ff-gotu { font-family: 'Gotu', 'Noto Sans Devanagari', sans-serif; }
      `}</style>

      {/* Heading — centered vertically between top of page and the paragraph below */}
      <div className="flex items-center justify-center w-full max-w-3xl pt-[7.875rem] pb-8">
        <motion.h1 className="flex items-center justify-center gap-3">
          <Leaf className="w-6 h-6 text-[#E5A93C] shrink-0" strokeWidth={1.75} />
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
        </motion.h1>
      </div>

      <div className="max-w-3xl w-full text-center">
        <p className="text-center text-[15px] text-[#C9C3AE] max-w-md mx-auto">
          Farmers list what they've harvested. Households and businesses buy it
          direct — no middlemen.
        </p>
        {onLogout && (
          <LiquidButton
            label="Log out"
            onClick={onLogout}
            size="xs"
            decor={false}
            className="mx-auto mt-4 bg-transparent text-[#8A8468] hover:text-[#C9A227] hover:bg-transparent"
          />
        )}

        <div className="mt-14 grid grid-cols-1 sm:grid-cols-2 gap-5 pb-10">
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