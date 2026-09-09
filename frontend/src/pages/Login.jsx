import React, { useState } from "react";
import {
  Leaf,
  ArrowLeft,
  Eye,
  EyeOff,
  Sprout,
  Store,
  RefreshCcw,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

const FIELD_FOCUS = `.fm-field:focus { border-color: #C9A227; }`;

function Field({ label, error, children }) {
  return (
    <label className="block mt-4 text-sm">
      <span className="block text-[#C9C3AE] mb-1.5">{label}</span>
      {children}

      {error && (
        <span className="block text-xs text-[#C4544A] mt-1">{error}</span>
      )}
    </label>
  );
}

// Role-specific presentation copy + accent icon
const ROLE_COPY = {
  farmer: {
    icon: Sprout,
    heading: "Welcome back, Farmer",
    tagline: "Sell your harvest directly to households and businesses.",
    accent: "Sell direct. Reach buyers. Keep control.",
    register: "Create a farmer account",
    switchLabel: "Shopping instead? Continue as a consumer",
    switchRole: "consumer",
  },
  consumer: {
    icon: Store,
    heading: "Welcome back",
    tagline:
      "Shop farm-direct produce at a fair price, or unlock business buying with your GSTIN.",
    accent: "Discover produce. Buy farm-direct.",
    register: "Create a consumer account",
    switchLabel: "Selling produce? Continue as a farmer",
    switchRole: "farmer",
  },
};

export default function Login({
  role = "consumer",
  onSwitchToRegister,
  onSwitchToDeveloperAccess,
  onSwitchRole,
  onBack,
}) {
  const { login } = useAuth();

  const copy = ROLE_COPY[role] || ROLE_COPY.consumer;
  const RoleIcon = copy.icon;

  const [form, setForm] = useState({
    username: "",
    password: "",
  });

  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState(null);

  function update(field, value) {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));

    // Clear field error when user starts correcting it
    setErrors((prev) => ({
      ...prev,
      [field]: "",
    }));

    // Clear server error when user changes the form
    if (serverError) {
      setServerError(null);
    }
  }

  function validate() {
    const e = {};

    if (!form.username.trim()) {
      e.username = "Enter your username";
    }

    if (!form.password) {
      e.password = "Enter your password";
    }

    return e;
  }

  async function handleSubmit(ev) {
    ev.preventDefault();

    // Clear previous errors
    setServerError(null);

    const validationErrors = validate();

    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setSubmitting(true);

    try {
      await login({
        username: form.username.trim(),
        password: form.password,
      });
    } catch (err) {
      /*
       * Handle Axios errors.
       *
       * Axios errors usually contain:
       * err.response.status
       * err.response.data
       *
       * For a 404, the backend route itself may not exist,
       * so don't show the raw Axios error to the user.
       */

      const status = err?.response?.status;

      if (status === 404) {
        setServerError(
          "Login service is currently unavailable. Please try again later."
        );
      } else if (status === 401) {
        setServerError("Incorrect email or password. Please try again.");
      } else if (status === 403) {
        setServerError("You are not authorized to log in.");
      } else if (status === 400) {
        setServerError(
          err?.response?.data?.message ||
            "Please check your login details."
        );
      } else if (status >= 500) {
        setServerError(
          "We couldn't connect to the service. Please try again."
        );
      } else if (err?.code === "ERR_NETWORK") {
        setServerError(
          "Unable to connect to the server. Please check your internet connection."
        );
      } else {
        setServerError(
          err?.response?.data?.message ||
            err?.message ||
            "Could not log in. Please try again."
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="min-h-screen w-full bg-[#14140F] text-[#F3ECDD] flex items-center justify-center px-5"
      style={{
        fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');

        .ff-display {
          font-family: 'Fraunces', ui-serif, Georgia, serif;
        }

        ${FIELD_FOCUS}
      `}</style>

      <div className="max-w-md w-full py-12">
        {/* Logo */}
        <div className="flex items-center gap-2 justify-center mb-8">
          <Leaf className="w-6 h-6 text-[#C9A227]" strokeWidth={1.75} />

          <span className="ff-display text-2xl tracking-tight">
            Kheti Seedha
          </span>
        </div>

        {/* Role accent icon */}
        <div className="flex justify-center mb-4">
          <span className="w-12 h-12 border border-[#33301F] bg-[#1D1C14] flex items-center justify-center">
            <RoleIcon
              className="w-6 h-6 text-[#C9A227]"
              strokeWidth={1.5}
            />
          </span>
        </div>

        {/* Heading */}
        <h1 className="ff-display text-3xl text-center leading-tight">
          {copy.heading}
        </h1>

        <p className="text-center text-sm text-[#C9C3AE] mt-2 max-w-sm mx-auto">
          {copy.tagline}
        </p>

        <p className="text-center text-[11px] uppercase tracking-widest text-[#8A8468] mt-4">
          {copy.accent}
        </p>

        {/* Server Error */}
        {serverError && (
          <div
            role="alert"
            className="mt-6 border border-[#C4544A]/40 bg-[#C4544A]/10 px-4 py-3 text-sm text-[#C4544A]"
          >
            {serverError}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="mt-6" noValidate>
          {/* Username */}
          <Field label="Username" error={errors.username}>
            <input
              type="text"
              value={form.username}
              onChange={(e) => update("username", e.target.value)}
              placeholder="your_username"
              autoComplete="username"
              disabled={submitting}
              className="fm-field"
              style={{
                width: "100%",
                border: "1px solid #4A4630",
                background: "#14140F",
                color: "#F3ECDD",
                padding: "0.6rem 0.75rem",
                fontSize: "0.875rem",
                outline: "none",
              }}
            />
          </Field>

          {/* Password */}
          <Field label="Password" error={errors.password}>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                disabled={submitting}
                className="fm-field pr-10"
                style={{
                  width: "100%",
                  border: "1px solid #4A4630",
                  background: "#14140F",
                  color: "#F3ECDD",
                  padding: "0.6rem 0.75rem",
                  fontSize: "0.875rem",
                  outline: "none",
                }}
              />

              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                disabled={submitting}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8A8468] hover:text-[#C9A227]"
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </Field>

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-6 py-2.5 bg-[#C9A227] text-[#14140F] text-sm font-medium hover:bg-[#D4AE3D] active:bg-[#B88E1E] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {/* Register */}
        <p className="text-center text-sm text-[#C9C3AE] mt-6">
          Don't have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-[#C9A227] hover:text-[#D4AE3D] transition-colors"
          >
            {copy.register}
          </button>
        </p>

        {/* Developer Access */}
        {onSwitchToDeveloperAccess && (
          <p className="text-center text-sm text-[#C9C3AE] mt-2">
            <button
              type="button"
              onClick={onSwitchToDeveloperAccess}
              className="text-[#8A8468] hover:text-[#C9A227] transition-colors text-xs"
            >
              Developer Access
            </button>
          </p>
        )}

        {/* Switch role (secondary) */}
        {onSwitchRole && (
          <p className="text-center text-sm text-[#C9C3AE] mt-4">
            <button
              type="button"
              onClick={() => onSwitchRole(copy.switchRole)}
              className="inline-flex items-center gap-1.5 text-[#8A8468] hover:text-[#C9A227] transition-colors text-sm"
            >
              <RefreshCcw className="w-3.5 h-3.5" />
              {copy.switchLabel}
            </button>
          </p>
        )}

        {/* Back */}
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1.5 mx-auto mt-6 text-sm text-[#8A8468] hover:text-[#C9A227] transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to role selection
          </button>
        )}
      </div>
    </div>
  );
}
