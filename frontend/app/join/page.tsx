"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function Join() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function join(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const c = code.trim().toUpperCase();
    try {
      await api(`/api/classrooms/${c}`);
      sessionStorage.setItem("mindstage-name", name.trim() || "Student");
      router.push(`/class/${c}`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form onSubmit={join} className="mx-auto mt-10 max-w-md space-y-4 rounded-2xl border border-line bg-panel p-8">
      <h1 className="font-display text-3xl">Join a class</h1>
      <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="Class code" maxLength={6} required
        className="w-full rounded-lg border border-line bg-ink px-4 py-3 text-center text-2xl uppercase tracking-[0.4em] outline-none focus:border-gold" />
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" maxLength={40} required
        className="w-full rounded-lg border border-line bg-ink px-4 py-3 outline-none focus:border-gold" />
      <button className="w-full rounded-full bg-gold py-3 font-semibold text-ink">Join</button>
      {error && <p className="text-sm text-red-400">{error}</p>}
    </form>
  );
}
