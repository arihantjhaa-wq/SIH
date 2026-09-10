import React from "react";
import { Navigate, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

/**
 * ProtectedRoute — wrapper for authenticated-only routes.
 *
 * Usage:
 *   <Route element={<ProtectedRoute />}>
 *     <Route path="/farmer" element={<FarmerPortal />} />
 *   </Route>
 *
 * Or with role restriction:
 *   <Route element={<ProtectedRoute allowedRole="farmer" />}>
 *     <Route path="/farmer" element={<FarmerPortal />} />
 *   </Route>
 */
export default function ProtectedRoute({ allowedRole, children }) {
  const { user, isAuthenticated, loading } = useAuth();
  const location = useLocation();

  // While loading, show nothing (or a minimal spinner) — don't redirect yet
  if (loading) {
    return (
      <div
        className="min-h-screen w-full bg-[#14140F] text-[#C9A227] flex items-center justify-center"
        style={{ fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif" }}
      >
        <p className="font-serif text-lg">Loading…</p>
      </div>
    );
  }

  // Not authenticated — redirect to login, preserving intended destination
  if (!isAuthenticated || !user) {
    return <Navigate to="/" replace state={{ from: location }} />;
  }

  // Role check (if provided)
  if (allowedRole) {
    const userRole = user.isDeveloper ? "developer" : (user.role || "").toLowerCase();
    if (userRole !== allowedRole.toLowerCase()) {
      // Wrong role for this route — redirect to appropriate portal or home
      if (user.isDeveloper) return <Navigate to="/developer" replace />;
      if (userRole === "farmer") return <Navigate to="/farmer" replace />;
      if (userRole === "consumer") return <Navigate to="/consumer" replace />;
      return <Navigate to="/" replace />;
    }
  }

  // Render children or outlet
  return children ?? <Outlet />;
}