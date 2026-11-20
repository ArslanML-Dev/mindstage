"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, tokenKey } from "@/lib/api";

export default function NewClass() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const room = await api<{ code: string; teacher_token: string }>("/api/classrooms", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim() || "My class" }),
      });
      localStorage.setItem(tokenKey(room.code), room.teacher_token);
      router.push(`/teach/${room.code}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={create} className="mx-auto mt-10 max-w-md space-y-4 rounded-2xl border border-line bg-panel p-8">
      <h1 className="font-display text-3xl">Start a class</h1>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Biology 9A — Photosynthesis"
        className="w-full rounded-lg border border-line bg-ink px-4 py-3 outline-none focus:border-gold" />
      <button disabled={busy} className="w-full rounded-full bg-gold py-3 font-semibold text-ink disabled:opacity-60">
        {busy ? "Creating…" : "Create class"}
      </button>
      {error && <p className="text-sm text-red-400">{error}</p>}
    </form>
  );
}
