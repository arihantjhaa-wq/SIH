import React, { useState } from "react";
import {
  Leaf,
  ArrowLeft,
  Eye,
  EyeOff,
  Sprout,
  Store,
  RefreshCcw,
  Mail,
  Lock,
} from "lucide-react";
import { motion, AnimatePresence, useMotionValue, useTransform } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import DancingLetters from "../components/ui/dancing-letters";
import { LiquidButton } from "../components/ui/liquid-glass-button";

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
  const navigate = useNavigate();

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
  const [focusedInput, setFocusedInput] = useState(null);

  // 3D card tilt effect
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(mouseY, [-300, 300], [8, -8]);
  const rotateY = useTransform(mouseX, [-300, 300], [-8, 8]);

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    mouseX.set(e.clientX - rect.left - rect.width / 2);
    mouseY.set(e.clientY - rect.top - rect.height / 2);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

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
      const returnedUser = await login({
        username: form.username.trim(),
        password: form.password,
      });

      // AuthContext state is already committed (setUser ran). Navigate to
      // the portal that matches this login flow — using the route param as
      // the canonical source of truth fixes any casing drift ("/farmer" param
      // is always lowercase, regardless of what user.role returns).
      const devFlag = !!(returnedUser?.isDeveloper || returnedUser?._isDeveloper);
      const dest = devFlag ? "/developer" : `/${role}`;
      navigate(dest, { replace: true });
    } catch (err) {
      const status = err?.response?.status;

      if (status === 404) {
        setServerError(
          "Login service is currently unavailable. Please try again later."
        );
      } else if (status === 401) {
        setServerError("Incorrect username or password. Please try again.");
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
      className="min-h-screen w-full bg-[#0d0d12] text-white relative overflow-hidden flex items-center justify-center px-5"
      style={{ fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif" }}
    >
      {/* Purple gradient backdrop */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-500/40 via-purple-700/50 to-black" />

      {/* Amethyst glow blobs */}
      <motion.div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[100vh] h-[60vh] rounded-b-full bg-purple-300/20 blur-[60px]"
        animate={{ opacity: [0.15, 0.3, 0.15], scale: [0.98, 1.02, 0.98] }}
        transition={{ duration: 8, repeat: Infinity, repeatType: "mirror" }}
      />
      <motion.div
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[90vh] h-[90vh] rounded-t-full bg-purple-400/20 blur-[60px]"
        animate={{ opacity: [0.3, 0.5, 0.3], scale: [1, 1.1, 1] }}
        transition={{ duration: 6, repeat: Infinity, repeatType: "mirror", delay: 1 }}
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="w-full max-w-md relative z-10 py-12"
        style={{ perspective: 1500 }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5 justify-center mb-8">
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

        <motion.div
          className="relative"
          style={{ rotateX, rotateY }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          {/* Glass card — the new sign-in-card-2 look */}
          <div className="relative rounded-2xl overflow-hidden border border-white/[0.05] bg-black/40 backdrop-blur-xl shadow-2xl p-6">
            {/* Card inner pattern */}
            <div
              className="absolute inset-0 opacity-[0.03] pointer-events-none"
              style={{
                backgroundImage: `linear-gradient(135deg, white 0.5px, transparent 0.5px), linear-gradient(45deg, white 0.5px, transparent 0.5px)`,
                backgroundSize: "30px 30px",
              }}
            />

            {/* Role accent icon */}
            <div className="flex justify-center mb-4">
              <motion.span
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", duration: 0.8 }}
                className="w-12 h-12 rounded-full border border-white/10 bg-white/5 flex items-center justify-center"
              >
                <RoleIcon className="w-6 h-6 text-[#C9A227]" strokeWidth={1.5} />
              </motion.span>
            </div>

            {/* Heading */}
            <motion.h1
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-white to-white/80 text-center"
            >
              {copy.heading}
            </motion.h1>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-center text-xs text-white/60 mt-1"
            >
              {copy.tagline}
            </motion.p>

            {/* Server Error */}
            {serverError && (
              <div
                role="alert"
                className="mt-4 border border-[#C4544A]/40 bg-[#C4544A]/10 px-4 py-3 text-sm text-[#C4544A] rounded-lg"
              >
                {serverError}
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="mt-5 space-y-4" noValidate>
              {/* Username */}
              <div className="relative flex items-center overflow-hidden rounded-lg bg-white/5 border border-white/10 focus-within:border-white/20 focus-within:bg-white/10 transition-all duration-300">
                <Mail className={`absolute left-3 w-4 h-4 transition-all duration-300 ${
                  focusedInput === "username" ? "text-white" : "text-white/40"
                }`} />
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) => update("username", e.target.value)}
                  onFocus={() => setFocusedInput("username")}
                  onBlur={() => setFocusedInput(null)}
                  placeholder="Username"
                  autoComplete="username"
                  disabled={submitting}
                  className="w-full bg-transparent text-white placeholder:text-white/30 h-10 pl-10 pr-3 text-sm outline-none"
                />
              </div>
              {errors.username && (
                <span className="block text-xs text-[#C4544A] mt-1">{errors.username}</span>
              )}

              {/* Password */}
              <div className="relative flex items-center overflow-hidden rounded-lg bg-white/5 border border-white/10 focus-within:border-white/20 focus-within:bg-white/10 transition-all duration-300">
                <Lock className={`absolute left-3 w-4 h-4 transition-all duration-300 ${
                  focusedInput === "password" ? "text-white" : "text-white/40"
                }`} />
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={(e) => update("password", e.target.value)}
                  onFocus={() => setFocusedInput("password")}
                  onBlur={() => setFocusedInput(null)}
                  placeholder="Password"
                  autoComplete="current-password"
                  disabled={submitting}
                  className="w-full bg-transparent text-white placeholder:text-white/30 h-10 pl-10 pr-10 text-sm outline-none"
                />
                <LiquidButton
                  icon={showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  onClick={() => setShowPassword((prev) => !prev)}
                  disabled={submitting}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  size="xs"
                  decor={false}
                  className="absolute right-3 w-8 h-8 px-0 bg-transparent hover:bg-white/10"
                  style={{ top: "50%", transform: "translateY(-50%)" }}
                />
              </div>
              {errors.password && (
                <span className="block text-xs text-[#C4544A] mt-1">{errors.password}</span>
              )}

              {/* Submit */}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="submit"
                disabled={submitting}
                className="w-full relative group/button mt-2"
              >
                <div className="absolute inset-0 bg-white/10 rounded-lg blur-lg opacity-0 group-hover/button:opacity-70 transition-opacity duration-300" />
                <div className="relative overflow-hidden bg-white text-black font-medium h-10 rounded-lg transition-all duration-300 flex items-center justify-center">
                  <AnimatePresence mode="wait">
                    {submitting ? (
                      <motion.div
                        key="loading"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center justify-center"
                      >
                        <div className="w-4 h-4 border-2 border-black/70 border-t-transparent rounded-full animate-spin" />
                      </motion.div>
                    ) : (
                      <motion.span
                        key="button-text"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="text-sm font-medium"
                      >
                        Sign in
                      </motion.span>
                    )}
                  </AnimatePresence>
                </div>
              </motion.button>

              {/* Register */}
              {onSwitchToRegister && (
                <p className="text-center text-xs text-white/60 mt-3">
                  Don't have an account?{" "}
                  <LiquidButton
                    label={copy.register}
                    onClick={onSwitchToRegister}
                    size="xs"
                    decor={false}
                    className="bg-transparent hover:bg-white/10 text-white"
                  />
                </p>
              )}

              {/* Developer Access */}
              {onSwitchToDeveloperAccess && (
                <p className="text-center text-xs text-white/60 mt-1">
                  <LiquidButton
                    label="Developer Access"
                    onClick={onSwitchToDeveloperAccess}
                    size="xs"
                    decor={false}
                    className="bg-transparent text-white/40 hover:text-white/70 hover:bg-transparent"
                  />
                </p>
              )}

              {/* Switch role (secondary) */}
              {onSwitchRole && (
                <p className="text-center text-xs text-white/60 mt-1">
                  <LiquidButton
                    label={copy.switchLabel}
                    icon={<RefreshCcw className="w-3.5 h-3.5" />}
                    onClick={() => onSwitchRole(copy.switchRole)}
                    size="xs"
                    decor={false}
                    className="bg-transparent text-white/40 hover:text-white hover:bg-transparent"
                  />
                </p>
              )}

              {/* Back */}
              {onBack && (
                <LiquidButton
                  label="Back to role selection"
                  icon={<ArrowLeft className="w-3.5 h-3.5" />}
                  onClick={onBack}
                  size="xs"
                  decor={false}
                  className="mx-auto mt-4 bg-transparent text-white/40 hover:text-white hover:bg-transparent"
                />
              )}
            </form>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}