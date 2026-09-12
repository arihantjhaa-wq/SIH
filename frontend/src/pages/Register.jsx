import React, { useState } from "react";
import { Leaf, ArrowLeft, Eye, EyeOff } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import DancingLetters from "../components/ui/dancing-letters";
import { LiquidButton } from "../components/ui/liquid-glass-button";

function Field({ label, error, children }) {
  return (
    <label className="block mt-4 text-sm">
      <span className="block text-[#C9C3AE] mb-1.5">
        {label}
      </span>

      {children}

      {error && (
        <span className="block text-xs text-[#C4544A] mt-1">
          {error}
        </span>
      )}
    </label>
  );
}

const INPUT_STYLE = {
  width: "100%",
  border: "1px solid #4A4630",
  background: "#14140F",
  color: "#F3ECDD",
  padding: "0.6rem 0.75rem",
  fontSize: "0.875rem",
  outline: "none",
};

// Role-specific copy for Register
const ROLE_COPY_REGISTER = {
  farmer: {
    icon: "🌱",
    heading: "Create your farmer account",
    tagline: "Start selling your harvest directly to households and businesses.",
    accent: "List products. Set fair prices. Keep the margin.",
  },
  consumer: {
    icon: "🛒",
    heading: "Create your buyer account",
    tagline: "Shop farm-direct produce at a fair price, or unlock bulk rates with your GSTIN.",
    accent: "Discover produce. Buy direct from farmers.",
  },
};

export default function Register({
  role = "consumer",
  onSwitchToLogin,
  onBack
}) {
  const { register } = useAuth();
  const navigate = useNavigate();

  const copy = ROLE_COPY_REGISTER[role] || ROLE_COPY_REGISTER.consumer;

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    name: "",
    address: "",
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

    // Clear field validation error
    setErrors((prev) => ({
      ...prev,
      [field]: "",
    }));

    // Clear previous server error
    if (serverError) {
      setServerError(null);
    }
  }

  function validate() {
    const e = {};

    // Full name (display name)
    if (!form.name.trim()) {
      e.name = "Enter your full name";
    }

    // Username
    if (!form.username.trim()) {
      e.username = "Choose a username";
    } else if (form.username.trim().length < 3) {
      e.username = "Username must be at least 3 characters";
    }

    // Email
    if (!form.email.trim()) {
      e.email = "Enter your email";
    } else if (
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())
    ) {
      e.email = "Enter a valid email address";
    }

    // Address (optional but encouraged)
    // No hard validation — backend treats it as optional.

    // Password
    if (!form.password) {
      e.password = "Enter a password";
    } else if (form.password.length < 6) {
      e.password = "Password must be at least 6 characters";
    }

    // Confirm password
    if (!form.confirmPassword) {
      e.confirmPassword = "Confirm your password";
    } else if (form.password !== form.confirmPassword) {
      e.confirmPassword = "Passwords do not match";
    }

    return e;
  }

  async function handleSubmit(ev) {
    ev.preventDefault();

    // Clear previous server error
    setServerError(null);

    // Validate form
    const validationErrors = validate();

    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setSubmitting(true);

    try {
      // register() performs the signup AND auto-login, returning the user.
      // Navigate to the portal matching this flow once auth state is committed.
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        name: form.name.trim() || undefined,
        address: form.address.trim() || undefined,
        role,
      });
      navigate(`/${role}`, { replace: true });
    } catch (err) {
      /*
       * Axios error handling
       *
       * Axios errors normally provide:
       * err.response.status
       * err.response.data
       */

      const status = err?.response?.status;

      if (status === 400) {
        setServerError(
          err?.response?.data?.message ||
            "Invalid registration details. Please check your information."
        );
      } else if (status === 404) {
        setServerError(
          "Registration service is unavailable. Please try again later."
        );
      } else if (status === 409) {
        setServerError(
          err?.response?.data?.message ||
            "Username or email is already registered."
        );
      } else if (status === 422) {
        setServerError(
          err?.response?.data?.message ||
            "Some of the information you entered is invalid."
        );
      } else if (status >= 500) {
        setServerError(
          "Something went wrong on the server. Please try again later."
        );
      } else if (err?.code === "ERR_NETWORK") {
        setServerError(
          "Unable to connect to the server. Please check your connection."
        );
      } else {
        setServerError(
          err?.response?.data?.message ||
            err?.message ||
            "Could not create your account. Please try again."
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

        .fm-field:focus {
          border-color: #C9A227 !important;
        }
      `}</style>

      <div className="max-w-md w-full py-12">
        {/* Logo */}
        <div className="flex items-center gap-2.5 justify-center mb-6">
          <Leaf
            className="w-6 h-6 text-[#E5A93C]"
            strokeWidth={1.75}
          />

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

        {/* Role accent icon */}
        <div className="flex justify-center mb-4">
          <span className="w-12 h-12 border border-[#33301F] bg-[#1D1C14] flex items-center justify-center text-2xl">
            {copy.icon}
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

        {/* Registration Form */}
        <form
          onSubmit={handleSubmit}
          className="mt-6"
          noValidate
        >
          {/* Full name */}
          <Field
            label="Full name"
            error={errors.name}
          >
            <input
              type="text"
              value={form.name}
              onChange={(e) =>
                update("name", e.target.value)
              }
              placeholder="Ravi Kumar"
              autoComplete="name"
              disabled={submitting}
              className="fm-field"
              style={INPUT_STYLE}
            />
          </Field>

          {/* Address */}
          <Field
            label="Address"
            error={errors.address}
          >
            <input
              type="text"
              value={form.address}
              onChange={(e) =>
                update("address", e.target.value)
              }
              placeholder="Village / district / state"
              autoComplete="street-address"
              disabled={submitting}
              className="fm-field"
              style={INPUT_STYLE}
            />
          </Field>

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
              style={INPUT_STYLE}
            />
          </Field>

          {/* Email */}
          <Field
            label="Email"
            error={errors.email}
          >
            <input
              type="email"
              value={form.email}
              onChange={(e) =>
                update("email", e.target.value)
              }
              placeholder="you@example.com"
              autoComplete="email"
              disabled={submitting}
              className="fm-field"
              style={INPUT_STYLE}
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
                placeholder="At least 6 characters"
                autoComplete="new-password"
                disabled={submitting}
                className="fm-field pr-10"
                style={INPUT_STYLE}
              />

              <LiquidButton
                icon={showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                onClick={() => setShowPassword((prev) => !prev)}
                disabled={submitting}
                aria-label={showPassword ? "Hide password" : "Show password"}
                size="xs"
                decor={false}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 w-6 h-6 px-0"
                style={{ transform: "translateY(-50%)" }}
              />
            </div>
          </Field>

          {/* Confirm Password */}
          <Field
            label="Confirm password"
            error={errors.confirmPassword}
          >
            <input
              type={showPassword ? "text" : "password"}
              value={form.confirmPassword}
              onChange={(e) =>
                update("confirmPassword", e.target.value)
              }
              placeholder="Re-enter your password"
              autoComplete="new-password"
              disabled={submitting}
              className="fm-field"
              style={INPUT_STYLE}
            />
          </Field>

          {/* Register Button */}
          <LiquidButton
            label={submitting ? "Creating account…" : "Register"}
            type="submit"
            disabled={submitting}
            className="w-full mt-6"
          />
        </form>

        {/* Login */}
        <p className="text-center text-sm text-[#C9C3AE] mt-6">
          Already have an account?{" "}
          <LiquidButton
            label="Log in"
            size="xs"
            decor={false}
            onClick={onSwitchToLogin}
            className="bg-transparent text-[#C9A227] hover:text-[#D4AE3D] hover:bg-transparent"
          />
        </p>

        {/* Back */}
        {onBack && (
          <LiquidButton
            label="Back to role selection"
            icon={<ArrowLeft className="w-3.5 h-3.5" />}
            onClick={onBack}
            size="xs"
            decor={false}
            className="mx-auto mt-6 bg-transparent text-[#8A8468] hover:text-[#C9A227] hover:bg-transparent"
          />
        )}

      </div>
    </div>
  );
}