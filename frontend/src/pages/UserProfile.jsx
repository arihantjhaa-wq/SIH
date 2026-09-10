import React from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Mail,
  ShieldCheck,
  MapPin,
  User as UserIcon,
  Leaf,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { ProfileAvatar } from "../components/ProfileButton.jsx";

function safeText(v, fallback = "—") {
  if (v == null) return fallback;
  const s = String(v).trim();
  return s.length ? s : fallback;
}

function roleBadgeLabel(user) {
  const r = (user?.role || "").toLowerCase();
  if (r === "admin") return "Admin";
  if (r === "farmer") return "Farmer";
  if (r === "consumer") return "Consumer";
  if (user?.isDeveloper) return "Admin";
  // Fallback: show raw role if present, otherwise omit badge
  if (user?.role) return String(user.role);
  return null;
}

function addressLines(user) {
  const raw = user?.address;
  if (raw == null || String(raw).trim() === "") return null;
  const s = String(raw).trim();
  // Keep as-is; backend stores free-form "City, State" or similar.
  return s;
}

export default function UserProfile() {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="min-h-screen w-full bg-[#F3ECDD] flex items-center justify-center px-5">
        <p className="text-sm text-[#5C5842]">Loading profile…</p>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen w-full bg-[#14140F] text-[#F3ECDD] flex items-center justify-center px-5">
        <div className="max-w-md w-full text-center py-16">
          <p className="text-sm text-[#C9C3AE]">You need to sign in to view your profile.</p>
          <button
            type="button"
            onClick={() => navigate("/", { replace: true })}
            className="mt-4 px-4 py-2 bg-[#C9A227] text-[#14140F] text-sm font-medium hover:bg-[#D4AE3D] transition-colors"
          >
            Go to sign in
          </button>
        </div>
      </div>
    );
  }

  const displayName =
    (user.name && String(user.name).trim()) ||
    (user.username && String(user.username).trim()) ||
    (user.email && String(user.email).split("@")[0]) ||
    "Account";

  const badge = roleBadgeLabel(user);
  const addr = addressLines(user);

  return (
    <div
      className="min-h-screen w-full bg-[#F3ECDD] text-[#2A2820]"
      style={{ fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif" }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
        .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
      `}</style>

      <div className="bg-[#14140F] text-[#F3ECDD]">
        <header className="border-b border-[#33301F]">
          <div className="max-w-6xl mx-auto px-5 py-5 flex items-center justify-between gap-4">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="inline-flex items-center gap-1.5 text-sm text-[#C9C3AE] hover:text-[#C9A227] transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <div className="flex items-center gap-2">
              <Leaf className="w-5 h-5 text-[#E5A93C]" strokeWidth={1.75} />
              <span className="brand-logo">
                <span className="devanagari">कृषि</span>{" "}
                <span className="latin">Setu</span>
              </span>
              <span className="hidden sm:inline ml-2 text-[11px] uppercase tracking-wide border border-[#C9A227] text-[#C9A227] px-2 py-0.5">
                Profile
              </span>
            </div>
            <span className="w-[72px]" aria-hidden />
          </div>
        </header>
        <section className="max-w-6xl mx-auto px-5 pt-10 pb-8">
          <h1 className="ff-display text-3xl sm:text-4xl leading-[1.1]">Your profile</h1>
          <p className="mt-2 text-[15px] text-[#C9C3AE] max-w-xl">
            Account details from your AgriDirect sign-in. This page is read-only — existing
            authentication and permissions are unchanged.
          </p>
        </section>
      </div>

      <main className="max-w-6xl mx-auto px-5 py-8">
        <div className="max-w-2xl mx-auto">
          <div className="rounded-2xl border border-[#E4D6A7] bg-white shadow-sm overflow-hidden">
            {/* Identity header */}
            <div className="px-6 sm:px-8 pt-8 pb-6 flex flex-col items-center text-center">
              <ProfileAvatar user={user} size={72} />
              <h2 className="ff-display text-2xl text-[#14140F] mt-4 leading-tight break-words max-w-full">
                {safeText(displayName, "Account")}
              </h2>
              {badge && (
                <span className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-[#C9A227]/40 bg-[#C9A227]/10 px-3 py-1 text-xs font-medium tracking-wide uppercase text-[#7A5E00]">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  {badge}
                </span>
              )}
              <p className="mt-2 text-sm text-[#5C5842] break-all max-w-full">
                {safeText(user.email, "No email on file")}
              </p>
            </div>

            <div className="mx-6 sm:mx-8 border-t border-[#F0E6C5]" />

            {/* Details */}
            <dl className="px-6 sm:px-8 py-6 grid grid-cols-1 gap-6">
              <div>
                <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[#8A8468]">
                  <UserIcon className="w-3.5 h-3.5" /> Name / Username
                </dt>
                <dd className="mt-1.5 text-sm text-[#14140F] break-words">
                  <span className="font-medium">{safeText(displayName)}</span>
                  {user.username && String(user.username).trim() && String(user.username).trim() !== displayName && (
                    <span className="text-[#5C5842]"> · @{String(user.username).trim()}</span>
                  )}
                </dd>
              </div>

              <div>
                <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[#8A8468]">
                  <Mail className="w-3.5 h-3.5" /> Email
                </dt>
                <dd className="mt-1.5 text-sm break-all">
                  {user.email ? (
                    <a href={`mailto:${user.email}`} className="text-[#1B3A2B] hover:underline">
                      {user.email}
                    </a>
                  ) : (
                    <span className="text-[#8A8468]">No email on file</span>
                  )}
                </dd>
              </div>

              <div>
                <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[#8A8468]">
                  <ShieldCheck className="w-3.5 h-3.5" /> Account role
                </dt>
                <dd className="mt-1.5">
                  {badge ? (
                    <span className="inline-flex rounded-full bg-[#1B3A2B] text-white px-3 py-1 text-xs font-medium tracking-wide uppercase">
                      {badge}
                    </span>
                  ) : (
                    <span className="text-sm text-[#8A8468]">No role assigned</span>
                  )}
                  <p className="mt-1 text-xs text-[#8A8468]">
                    Visual badge only — permissions are enforced server-side.
                  </p>
                </dd>
              </div>

              <div>
                <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[#8A8468]">
                  <MapPin className="w-3.5 h-3.5" /> Saved address
                </dt>
                <dd className="mt-1.5 text-sm">
                  {addr ? (
                    <span className="text-[#2A2820] break-words whitespace-pre-wrap">{addr}</span>
                  ) : (
                    <span className="inline-flex rounded-lg border border-dashed border-[#D8CBA1] bg-[#FBF7EC] px-3 py-2 text-sm text-[#8A8468]">
                      No saved address
                    </span>
                  )}
                </dd>
              </div>
            </dl>

            <div className="px-6 sm:px-8 pb-6 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-[#D8CBA1] text-[#1B3A2B] hover:bg-[#FBF7EC] transition-colors"
              >
                <ArrowLeft className="w-4 h-4" /> Back
              </button>
              <button
                type="button"
                onClick={() => navigate("/", { replace: false })}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-[#1B3A2B] text-white hover:bg-[#0E1F17] transition-colors"
              >
                Home
              </button>
            </div>
          </div>

          <p className="mt-4 text-center text-xs text-[#8A8468]">
            Prefer to switch roles or sign out? Use the menu in the header.
          </p>
        </div>
      </main>
    </div>
  );
}
