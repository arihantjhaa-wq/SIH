import React, { useState } from "react";
import { Leaf, ArrowLeft, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

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

const INPUT_STYLE = {
  width: "100%",
  border: "1px solid #4A4630",
  background: "#14140F",
  color: "#F3ECDD",
  padding: "0.6rem 0.75rem",
  fontSize: "0.875rem",
  outline: "none",
};

export default function Register({ onSwitchToLogin, onBack }) {
  const { register } = useAuth();
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState(null);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function validate() {
    const e = {};
    if (!form.username.trim()) e.username = "Choose a username";
    else if (form.username.trim().length < 3)
      e.username = "Username must be at least 3 characters";
    if (!form.email.trim()) e.email = "Enter your email";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      e.email = "Enter a valid email address";
    if (!form.password) e.password = "Enter a password";
    else if (form.password.length < 6)
      e.password = "Password must be at least 6 characters";
    if (!form.confirmPassword) e.confirmPassword = "Confirm your password";
    else if (form.password !== form.confirmPassword)
      e.confirmPassword = "Passwords do not match";
    return e;
  }

  async function handleSubmit(ev) {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length > 0) return;

    setSubmitting(true);
    setServerError(null);
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
      });
    } catch (err) {
      setServerError(err.message || "Could not register");
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
          <Leaf className="w-6 h-6 text-[#C9A227]" strokeWidth={1.75} />
          <span className="ff-display text-2xl tracking-tight">Kheti Seedha</span>
        </div>

        <h1 className="ff-display text-3xl text-center leading-tight">
          Create your account
        </h1>
        <p className="text-center text-sm text-[#C9C3AE] mt-2">
          Join Kheti Seedha to buy farm-direct or list your harvest.
        </p>

        {serverError && (
          <div className="mt-6 border border-[#C4544A]/40 bg-[#C4544A]/10 px-4 py-3 text-sm text-[#C4544A]">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6">
          <Field label="Username" error={errors.username}>
            <input
              value={form.username}
              onChange={(e) => update("username", e.target.value)}
              placeholder="your_username"
              className="fm-field"
              style={INPUT_STYLE}
            />
          </Field>

          <Field label="Email" error={errors.email}>
            <input
              type="email"
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              placeholder="you@example.com"
              className="fm-field"
              style={INPUT_STYLE}
            />
          </Field>

          <Field label="Password" error={errors.password}>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="At least 6 characters"
                className="fm-field pr-10"
                style={INPUT_STYLE}
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8A8468] hover:text-[#C9A227]"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </Field>

          <Field label="Confirm password" error={errors.confirmPassword}>
            <input
              type={showPassword ? "text" : "password"}
              value={form.confirmPassword}
              onChange={(e) => update("confirmPassword", e.target.value)}
              placeholder="Re-enter your password"
              className="fm-field"
              style={INPUT_STYLE}
            />
          </Field>

          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-6 py-2.5 bg-[#C9A227] text-[#14140F] text-sm font-medium hover:bg-[#D4AE3D] active:bg-[#B88E1E] transition-colors disabled:opacity-60"
          >
            {submitting ? "Creating account…" : "Register"}
          </button>
        </form>

        <p className="text-center text-sm text-[#C9C3AE] mt-6">
          Already have an account?{" "}
          <button
            onClick={onSwitchToLogin}
            className="text-[#C9A227] hover:text-[#D4AE3D] transition-colors"
          >
            Log in
          </button>
        </p>

        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 mx-auto mt-6 text-sm text-[#8A8468] hover:text-[#C9A227] transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to home
          </button>
        )}
      </div>
    </div>
  );
}
