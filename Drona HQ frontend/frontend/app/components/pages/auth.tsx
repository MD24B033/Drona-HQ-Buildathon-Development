"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff } from "lucide-react";

import { supabase } from "../../lib/supabase/client";
import { getSession } from "../../lib/supabase/session";

export default function AuthPage() {
  const router = useRouter();

  const [isSignUp, setIsSignUp] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);

  const [showPassword, setShowPassword] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  /*
   * If the user is already logged in,
   * don't show the login page.
   * Send them directly to the dashboard.
   */
  useEffect(() => {
    let mounted = true;

    const checkExistingSession = async () => {
      const session = await getSession();

      if (!mounted) return;

      if (session) {
        router.replace("/onboarding");
        return;
      }

      setCheckingSession(false);
    };

    checkExistingSession();

    return () => {
      mounted = false;
    };
  }, [router]);

  const clearMessages = () => {
    setMessage("");
    setError("");
  };

  /*
   * EMAIL LOGIN / SIGNUP
   */
  const handleAuth = async () => {
    clearMessages();

    const cleanEmail = email.trim();

    if (!cleanEmail || !password) {
      setError("Please enter your email and password.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);

    try {
      /*
       * SIGN UP
       */
      if (isSignUp) {
        const { data, error } = await supabase.auth.signUp({
          email: cleanEmail,
          password,
        });

        if (error) {
          throw error;
        }

        /*
         * If Supabase email confirmation is enabled,
         * there won't be a session immediately.
         */
        if (!data.session) {
          setMessage(
            "Account created successfully. Please check your email and confirm your account before signing in."
          );

          setIsSignUp(false);
          setPassword("");

          return;
        }

        /*
         * Session exists immediately.
         * Go to dashboard.
         */
        router.replace("/onboarding");

        return;
      }

      /*
       * LOGIN
       */
      const { data, error } = await supabase.auth.signInWithPassword({
        email: cleanEmail,
        password,
      });

      if (error) {
        throw error;
      }

      /*
       * Make sure a session actually exists.
       */
      if (!data.session) {
        setError("Login succeeded, but no session was created.");
        return;
      }

      /*
       * Login successful.
       */
      router.replace("/onboarding");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  /*
   * GOOGLE LOGIN
   */
  const handleGoogle = async () => {
    clearMessages();
    setGoogleLoading(true);

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (error) {
        throw error;
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to continue with Google.");
      }

      setGoogleLoading(false);
    }
  };

  /*
   * SWITCH LOGIN / SIGNUP
   */
  const switchMode = () => {
    clearMessages();
    setPassword("");
    setIsSignUp((current) => !current);
  };

  /*
   * Prevent the login UI from flashing
   * while we check the existing session.
   */
  if (checkingSession) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center text-white">
        <div className="text-gray-400 animate-pulse">
          Checking session...
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#070b14] flex items-center justify-center px-4 text-white">
      {/* Background Glow */}
      <div className="absolute top-[-120px] left-[-120px] w-[350px] h-[350px] bg-indigo-500/30 rounded-full blur-3xl" />

      <div className="absolute bottom-[-120px] right-[-120px] w-[350px] h-[350px] bg-cyan-500/20 rounded-full blur-3xl" />

      {/* Glass Card */}
      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md rounded-[32px] border border-white/10 bg-white/5 backdrop-blur-2xl shadow-[0_0_80px_rgba(99,102,241,0.15)] p-8"
      >
        {/* Tabs */}
        <div className="flex bg-white/5 rounded-2xl p-1 mb-8 border border-white/10">
          <button
            type="button"
            onClick={() => {
              setIsSignUp(false);
              clearMessages();
            }}
            className={`flex-1 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
              !isSignUp
                ? "bg-indigo-500 text-white shadow-lg"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Sign In
          </button>

          <button
            type="button"
            onClick={() => {
              setIsSignUp(true);
              clearMessages();
            }}
            className={`flex-1 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
              isSignUp
                ? "bg-indigo-500 text-white shadow-lg"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Sign Up
          </button>
        </div>

        {/* Heading */}
        <AnimatePresence mode="wait">
          <motion.div
            key={isSignUp ? "signup" : "signin"}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
          >
            <h1 className="text-4xl font-bold text-center mb-2">
              {isSignUp ? "Create Account" : "Welcome Back"}
            </h1>

            <p className="text-center text-gray-400 mb-8">
              {isSignUp
                ? "Join and start your journey"
                : "Sign in to continue"}
            </p>
          </motion.div>
        </AnimatePresence>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="mb-5 rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Success Message */}
        <AnimatePresence>
          {message && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="mb-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300"
            >
              {message}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Inputs */}
        <div className="space-y-5">
          {/* Email */}
          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            autoComplete="email"
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleAuth();
              }
            }}
            className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 outline-none focus:border-indigo-500 transition-all text-white placeholder:text-gray-500"
          />

          {/* Password */}
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              autoComplete={
                isSignUp ? "new-password" : "current-password"
              }
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleAuth();
                }
              }}
              className="w-full h-14 rounded-2xl bg-white/5 border border-white/10 px-5 pr-14 outline-none focus:border-indigo-500 transition-all text-white placeholder:text-gray-500"
            />

            <button
              type="button"
              onClick={() =>
                setShowPassword((current) => !current)
              }
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
            >
              {showPassword ? (
                <EyeOff size={20} />
              ) : (
                <Eye size={20} />
              )}
            </button>
          </div>

          {/* Main Button */}
          <motion.button
            type="button"
            whileTap={{ scale: 0.97 }}
            whileHover={{ scale: 1.01 }}
            onClick={handleAuth}
            disabled={loading || googleLoading}
            className="w-full h-14 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 font-semibold text-white shadow-lg shadow-indigo-500/20 hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading
              ? isSignUp
                ? "Creating Account..."
                : "Signing In..."
              : isSignUp
                ? "Create Account"
                : "Sign In"}
          </motion.button>

          {/* Divider */}
          <div className="flex items-center gap-4 py-2">
            <div className="flex-1 h-px bg-white/10" />

            <span className="text-sm text-gray-500">
              OR
            </span>

            <div className="flex-1 h-px bg-white/10" />
          </div>

          {/* Google */}
          <motion.button
            type="button"
            whileTap={{ scale: 0.97 }}
            whileHover={{ scale: 1.01 }}
            onClick={handleGoogle}
            disabled={loading || googleLoading}
            className="w-full h-14 rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {googleLoading
              ? "Connecting..."
              : "Continue with Google"}
          </motion.button>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-gray-500 mt-8">
          {isSignUp
            ? "Already have an account?"
            : "Don’t have an account?"}{" "}

          <button
            type="button"
            onClick={switchMode}
            className="text-indigo-400 hover:text-indigo-300 font-medium"
          >
            {isSignUp ? "Sign In" : "Sign Up"}
          </button>
        </p>
      </motion.div>
    </div>
  );
}