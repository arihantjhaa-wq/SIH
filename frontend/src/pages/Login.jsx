import React, { useState } from "react";
import { Leaf, ArrowLeft, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

const FIELD_FOCUS = `.fm-field:focus { border-color: #C9A227; }`;

function Field({ label, error, children }) {
  return (
    <label className="block mt-4 text-sm">
      <span className="block text-[#C9C3AE] mb-1.5">{label}</span>
      {children}

      {error && (
        <span className="block text-xs text-[#C4544A] mt-1">
          {error}
        </span>
      )}
    </label>
  );
}

export default function Login({
  onSwitchToRegister,
  onSwitchToDeveloperAccess,
  onBack,
}) {
  const { login } = useAuth();

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
        setServerError(
          "Invalid username or password."
        );
      } else if (status === 403) {
        setServerError(
          "You are not authorized to log in."
        );
      } else if (status === 400) {
        setServerError(
          err?.response?.data?.message ||
            "Please check your login details."
        );
      } else if (status >= 500) {
        setServerError(
          "Something went wrong on the server. Please try again later."
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
        fontFamily:
          "'Work Sans', ui-sans-serif, system-ui, sans-serif",
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
        <div className="flex items-center gap-2 justify-center mb-6">
          <Leaf
            className="w-6 h-6 text-[#C9A227]"
            strokeWidth={1.75}
          />

          <span className="ff-display text-2xl tracking-tight">
            Kheti Seedha
          </span>
        </div>

        {/* Heading */}
        <h1 className="ff-display text-3xl text-center leading-tight">
          Welcome back
        </h1>

        <p className="text-center text-sm text-[#C9C3AE] mt-2">
          Log in to continue buying or listing farm-direct produce.
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
          <Field
            label="Username"
            error={errors.username}
          >
            <input
              type="text"
              value={form.username}
              onChange={(e) =>
                update("username", e.target.value)
              }
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
          <Field
            label="Password"
            error={errors.password}
          >
            <div className="relative">

              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(e) =>
                  update("password", e.target.value)
                }
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
                onClick={() =>
                  setShowPassword((prev) => !prev)
                }
                disabled={submitting}
                aria-label={
                  showPassword
                    ? "Hide password"
                    : "Show password"
                }
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
            {submitting ? "Logging in…" : "Log in"}
          </button>
        </form>

        {/* Developer Access */}
        <p className="text-center text-sm text-[#C9C3AE] mt-6">
          <button
            type="button"
            onClick={onSwitchToDeveloperAccess}
            className="text-[#8A8468] hover:text-[#C9A227] transition-colors text-xs"
          >
            Developer Access
          </button>
        </p>

        {/* Register */}
        <p className="text-center text-sm text-[#C9C3AE] mt-2">
          Don't have an account?{" "}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-[#C9A227] hover:text-[#D4AE3D] transition-colors"
          >
            Register
          </button>
        </p>

        {/* Back */}
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1.5 mx-auto mt-6 text-sm text-[#8A8468] hover:text-[#C9A227] transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to home
          </button>
        )}
      </div>
    </div>
  );
}
