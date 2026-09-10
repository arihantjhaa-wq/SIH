import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { User, LogOut, LayoutDashboard, ChevronDown, X } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

function initialsFor(user) {
  const src = (user?.name || user?.username || user?.email || "?").trim();
  const parts = src.split(/\s+/).filter(Boolean).slice(0, 2);
  const letters = parts.map((p) => p[0].toUpperCase());
  if (letters.length === 1 && src.length >= 2 && !src.includes(" ") && src.includes("@")) {
    // email-like single token: take first two letters before '@'
    const local = src.split("@")[0];
    return (local[0] + (local[1] || "")).toUpperCase();
  }
  return (letters.join("") || "?").slice(0, 2);
}

function ProfileAvatar({ user, size = 36 }) {
  const initials = initialsFor(user);
  return (
    <span
      aria-hidden
      className="inline-flex items-center justify-center rounded-full bg-[#C9A227] text-[#14140F] font-semibold select-none shrink-0"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.38) }}
    >
      {initials}
    </span>
  );
}

export default function ProfileButton({ user: propUser, onSwitch, onLogout }) {
  const { user: ctxUser } = useAuth();
  const user = propUser ?? ctxUser;
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const btnRef = useRef(null);

  const displayName =
    (user?.name && user.name.trim()) ||
    (user?.username && user.username.trim()) ||
    (user?.email && user.email.split("@")[0]) ||
    "Account";

  const roleLabel = (() => {
    const r = (user?.role || "").toLowerCase();
    if (r === "admin") return "Admin";
    if (r === "farmer") return "Farmer";
    if (r === "consumer") return "Consumer";
    if (user?.isDeveloper) return "Admin";
    return null;
  })();

  useEffect(() => {
    if (!open) return;
    function onDocClick(e) {
      if (!ref.current) return;
      if (ref.current.contains(e.target)) return;
      if (btnRef.current && btnRef.current.contains(e.target)) return;
      setOpen(false);
    }
    function onKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative">
      <button
        ref={btnRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close profile menu" : `Open profile menu for ${displayName}`}
        aria-expanded={open}
        aria-haspopup="menu"
        className="inline-flex items-center gap-2 rounded-full border border-[#4A4630] bg-[#1D1C14] pl-1 pr-2 py-1 text-sm text-[#F3ECDD] hover:border-[#C9A227] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C9A227]/60"
      >
        <ProfileAvatar user={user} size={32} />
        <span className="hidden sm:inline max-w-[10rem] truncate text-left leading-none">
          <span className="block text-[13px] font-medium leading-none">{displayName}</span>
          {roleLabel && (
            <span className="block text-[10px] uppercase tracking-wide text-[#C9C3AE] leading-none mt-0.5">
              {roleLabel}
            </span>
          )}
        </span>
        <ChevronDown
          className={`hidden sm:block w-3.5 h-3.5 text-[#8A8468] transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div
          ref={ref}
          role="menu"
          className="absolute right-0 mt-2 w-56 rounded-xl border border-[#E4D6A7] bg-white shadow-xl overflow-hidden z-50"
        >
          <div className="px-4 py-3 flex items-center gap-3 bg-[#FBF7EC] border-b border-[#E4D6A7]">
            <ProfileAvatar user={user} size={36} />
            <div className="min-w-0">
              <p className="text-sm font-medium text-[#14140F] truncate">{displayName}</p>
              <p className="text-xs text-[#5C5842] truncate">{user?.email || "No email on file"}</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close menu"
              className="ml-auto p-1 text-[#8A8468] hover:text-[#1B3A2B]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="py-1">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                navigate("/profile");
              }}
              className="w-full text-left px-4 py-2.5 text-sm text-[#2A2820] hover:bg-[#FBF7EC] flex items-center gap-2 focus-visible:outline-none focus-visible:bg-[#FBF7EC]"
            >
              <User className="w-4 h-4 text-[#5C5842]" /> Profile
            </button>

            {onSwitch && (
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  onSwitch();
                }}
                className="w-full text-left px-4 py-2.5 text-sm text-[#2A2820] hover:bg-[#FBF7EC] flex items-center gap-2 focus-visible:outline-none focus-visible:bg-[#FBF7EC]"
              >
                <LayoutDashboard className="w-4 h-4 text-[#5C5842]" /> Switch role
              </button>
            )}

            {onLogout && (
              <>
                <div className="mx-3 my-1 border-t border-[#F0E6C5]" />
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setOpen(false);
                    onLogout();
                  }}
                  className="w-full text-left px-4 py-2.5 text-sm text-[#7A2A22] hover:bg-[#FFF5F5] flex items-center gap-2 focus-visible:outline-none focus-visible:bg-[#FFF5F5]"
                >
                  <LogOut className="w-4 h-4" /> Log out
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export { ProfileAvatar, initialsFor };
