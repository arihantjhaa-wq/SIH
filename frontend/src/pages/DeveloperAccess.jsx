import React, { useState } from "react";
import { Leaf, ArrowLeft, Code } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import DancingLetters from "../components/ui/dancing-letters";
import { LiquidButton } from "../components/ui/liquid-glass-button";

export default function DeveloperAccess({ onSwitchToLogin, onBack }) {
  const { developerLogin } = useAuth();
  const navigate = useNavigate();
  const [developerKey, setDeveloperKey] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(ev) {
    ev.preventDefault();

    if (!developerKey.trim()) {
      setError("Please enter your developer key");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await developerLogin({ developerKey: developerKey.trim() });
      navigate("/developer", { replace: true });
    } catch (err) {
      setError(err.message || "Invalid developer key");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="min-h-screen w-full bg-[#14140F] text-[#F3ECDD] flex items-center justify-center px-5"
      style={{ fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif" }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
        .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
        .fm-field:focus { border-color: #C9A227; }
      `}</style>

      <div className="max-w-md w-full py-12">
        <div className="flex items-center gap-2 justify-center mb-6">
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
        </div>

        <div className="flex items-center gap-2 justify-center mb-2">
          <Code className="w-5 h-5 text-[#8A8468]" strokeWidth={1.5} />
          <h1 className="ff-display text-3xl text-center leading-tight">
            Developer Access
          </h1>
        </div>

        <p className="text-center text-sm text-[#C9C3AE] mt-2">
          Enter your developer key to access the application.
        </p>

        {error && (
          <div className="mt-6 border border-[#C4544A]/40 bg-[#C4544A]/10 px-4 py-3 text-sm text-[#C4544A]">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6">
          <label className="block text-sm">
            <span className="block text-[#C9C3AE] mb-1.5">Developer Key</span>
            <input
              type="password"
              value={developerKey}
              onChange={(e) => setDeveloperKey(e.target.value)}
              placeholder="Enter developer key"
              className="fm-field"
              style={{
                width: "100%",
                border: "1px solid #4A4630",
                background: "#14140F",
                color: "#F3ECDD",
                padding: "0.6rem 0.75rem",
                fontSize: "0.875rem",
                outline: "none"
              }}
              disabled={submitting}
            />
          </label>

          <LiquidButton
            label={submitting ? "Verifying…" : "Enter Developer Mode"}
            type="submit"
            disabled={submitting}
            className="w-full mt-6"
          />
        </form>

        <p className="text-center text-sm text-[#C9C3AE] mt-6">
          <LiquidButton
            label="← Back to normal login"
            onClick={onSwitchToLogin}
            size="xs"
            decor={false}
            className="bg-transparent text-[#C9A227] hover:text-[#D4AE3D] hover:bg-transparent"
          />
        </p>

        {onBack && (
          <LiquidButton
            label="Back to home"
            icon={<ArrowLeft className="w-3.5 h-3.5" />}
            onClick={onBack}
            size="sm"
            decor={false}
            className="mx-auto mt-4 bg-transparent text-[#8A8468] hover:text-[#C9A227] hover:bg-transparent"
          />
        )}
      </div>
    </div>
  );
}
