"use client";

import { Session, User } from "@supabase/supabase-js";
import { supabase } from "./client";

/**
 * Get the currently logged-in session.
 *
 * Returns null when the user is not logged in.
 */
export async function getSession(): Promise<Session | null> {
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();

  if (error) {
    console.error("Failed to get session:", error);
    return null;
  }

  return session;
}

/**
 * Get the currently logged-in user.
 *
 * Returns null when the user is not logged in.
 */
export async function getUser(): Promise<User | null> {
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error) {
    console.error("Failed to get user:", error);
    return null;
  }

  return user;
}

/**
 * Listen for login/logout/session changes.
 */
export function subscribeToAuthChanges(
  callback: (session: Session | null) => void
) {
  const {
    data: { subscription },
  } = supabase.auth.onAuthStateChange((_event, session) => {
    callback(session);
  });

  return subscription;
}

/**
 * Log the user out and return them to the auth page.
 */
export async function signOut() {
  const { error } = await supabase.auth.signOut();

  if (error) {
    console.error("Failed to sign out:", error);
    throw error;
  }

  window.location.replace("/auth");
}