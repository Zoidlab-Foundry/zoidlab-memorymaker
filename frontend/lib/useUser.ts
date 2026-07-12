"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { WhoAmI } from "./types";

export function useUser() {
  const [user, setUser] = useState<WhoAmI | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.whoami().then(setUser).catch(() => setUser({ authenticated: false })).finally(() => setLoading(false));
  }, []);
  return { user, loading, authed: !!user?.authenticated };
}
