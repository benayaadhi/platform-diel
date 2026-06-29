"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register, setToken } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [handle, setHandle] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { access_token } = await register(handle, email, password);
      setToken(access_token);
      router.push("/strategies/new");
      router.refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto">
      <h1 className="text-xl font-bold mb-4">Daftar</h1>
      <form onSubmit={submit} className="card p-5 space-y-4">
        <div>
          <label className="label">Handle (username)</label>
          <input className="input" value={handle} minLength={3}
                 onChange={(e) => setHandle(e.target.value)} required />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={email}
                 onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="label">Password (min 6)</label>
          <input className="input" type="password" value={password} minLength={6}
                 onChange={(e) => setPassword(e.target.value)} required />
        </div>
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? "Memproses…" : "Daftar"}
        </button>
        <p className="text-xs text-slate-500 text-center">
          Sudah punya akun?{" "}
          <Link href="/login" className="text-accent underline">Masuk</Link>
        </p>
      </form>
    </div>
  );
}
