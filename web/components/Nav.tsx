"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clearToken, isLoggedIn } from "@/lib/api";

export default function Nav() {
  const [authed, setAuthed] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setAuthed(isLoggedIn());
  }, []);

  function logout() {
    clearToken();
    setAuthed(false);
    router.push("/");
    router.refresh();
  }

  return (
    <header className="border-b border-edge bg-panel/60 backdrop-blur sticky top-0 z-10">
      <div className="mx-auto max-w-5xl px-4 h-14 flex items-center justify-between">
        <Link href="/" className="font-bold tracking-tight text-lg">
          DIEL<span className="text-accent">.</span>
          <span className="ml-2 text-xs font-normal text-slate-400">
            verified strategies
          </span>
        </Link>
        <nav className="flex items-center gap-2 text-sm">
          <Link href="/" className="btn-ghost">Leaderboard</Link>
          {authed ? (
            <>
              <Link href="/strategies/new" className="btn-primary">+ Strategi</Link>
              <button onClick={logout} className="btn-ghost">Keluar</button>
            </>
          ) : (
            <>
              <Link href="/login" className="btn-ghost">Masuk</Link>
              <Link href="/register" className="btn-primary">Daftar</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
