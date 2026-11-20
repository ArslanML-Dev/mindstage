"use client";
import { use, useEffect, useState } from "react";
import SceneView from "@/components/SceneView";
import { api, tokenKey, type LessonOut } from "@/lib/api";
import { useLive, type LiveMessage } from "@/lib/useLive";

type Stats = Record<string, number[]>; // "scene-question" -> counts per option

export default function TeacherConsole({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const [token, setToken] = useState<string | null>(null);
  const [data, setData] = useState<LessonOut | null>(null);
  const [scene, setScene] = useState(0);
  const [students, setStudents] = useState<string[]>([]);
  const [stats, setStats] = useState<Stats>({});
  const [doubts, setDoubts] = useState<{ student: string; question: string; answer: string }[]>([]);
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setToken(localStorage.getItem(tokenKey(code)));
    api<LessonOut>(`/api/classrooms/${code}/lesson`).then(setData).catch(() => {});
  }, [code]);

  const onMessage = (m: LiveMessage) => {
    if (m.type === "scene") setScene(m.index);
    if (m.type === "presence") setStudents(m.students);
    if (m.type === "stats") setStats((s) => ({ ...s, [`${m.scene}-${m.question}`]: m.counts }));
    if (m.type === "doubt") setDoubts((d) => [{ student: m.student, question: m.question, answer: m.answer }, ...d]);
  };
  const { connected, send } = useLive(code, `role=teacher&token=${encodeURIComponent(token ?? "")}`, onMessage, !!token);

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("notes", notes);
    if (file) form.append("file", file);
    try {
      setData(await api<LessonOut>(`/api/classrooms/${code}/lesson`, {
        method: "POST", headers: { "x-teacher-token": token ?? "" }, body: form,
      }));
      setScene(0);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (token === null) {
    return <p className="text-mist">This browser didn&apos;t create class {code}. Open it from the device you started it on.</p>;
  }

  const lesson = data?.lesson;
  const goto = (i: number) => send({ type: "goto", index: i });

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-mist">Students join at <b className="text-white">/join</b> with code</p>
          <p className="font-display text-5xl tracking-[0.3em] text-gold">{code}</p>
        </div>
        <div className="text-right text-sm text-mist">
          <p>{connected ? "● Live" : "○ Connecting…"} · {students.length} student{students.length === 1 ? "" : "s"}</p>
          <p className="max-w-xs truncate">{students.join(", ")}</p>
          {data && <p className="mt-1 text-xs">AI: {data.engine}</p>}
        </div>
      </div>

      {!lesson ? (
        <form onSubmit={generate} className="space-y-4 rounded-2xl border border-line bg-panel p-6">
          <h1 className="font-display text-3xl">Turn your notes into a lesson</h1>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={8}
            placeholder="Paste your notes here…"
            className="w-full rounded-lg border border-line bg-ink p-4 outline-none focus:border-gold" />
          <label className="block text-sm text-mist">
            …or upload a PDF, Word file, text file or a photo of your notes
            <input type="file" accept=".pdf,.docx,.txt,.md,.jpg,.jpeg,.png,.webp"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="mt-2 block text-sm" />
          </label>
          <button disabled={busy} className="rounded-full bg-gold px-6 py-3 font-semibold text-ink disabled:opacity-60">
            {busy ? "Directing your lesson… (~30 s)" : "Generate lesson"}
          </button>
          {error && <p className="text-sm text-red-400">{error}</p>}
        </form>
      ) : (
        <>
          <SceneView scene={lesson.scenes[scene]} index={scene} total={lesson.scenes.length} />
          <div className="flex items-center justify-between">
            <button onClick={() => goto(Math.max(0, scene - 1))} disabled={scene === 0}
              className="rounded-full border border-line px-5 py-2 disabled:opacity-40">← Previous</button>
            <div className="flex gap-2">
              {lesson.scenes.map((_, i) => (
                <button key={i} onClick={() => goto(i)} aria-label={`Scene ${i + 1}`}
                  className={`h-3 w-3 rounded-full ${i === scene ? "bg-gold" : "bg-line"}`} />
              ))}
            </div>
            <button onClick={() => goto(Math.min(lesson.scenes.length - 1, scene + 1))}
              disabled={scene === lesson.scenes.length - 1}
              className="rounded-full bg-gold px-5 py-2 font-semibold text-ink disabled:opacity-40">Next →</button>
          </div>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-line bg-panel p-5">
              <h3 className="font-semibold">Live checkpoint answers</h3>
              {lesson.scenes[scene].mcqs.map((q, qi) => {
                const counts = stats[`${scene}-${qi}`] ?? [0, 0, 0, 0];
                const total = counts.reduce((a, b) => a + b, 0) || 1;
                return (
                  <div key={qi} className="mt-4">
                    <p className="text-sm">{q.question}</p>
                    {q.options.map((o, oi) => (
                      <div key={oi} className="mt-1 flex items-center gap-2 text-xs">
                        <span className={`w-36 truncate ${oi === q.answer_index ? "text-gold" : "text-mist"}`}>{o}</span>
                        <div className="h-2 flex-1 rounded bg-line">
                          <div className={`h-2 rounded ${oi === q.answer_index ? "bg-gold" : "bg-mist"}`}
                            style={{ width: `${(counts[oi] / total) * 100}%` }} />
                        </div>
                        <span className="w-5 text-right">{counts[oi]}</span>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
            <div className="rounded-2xl border border-line bg-panel p-5">
              <h3 className="font-semibold">Student doubts (answered from your notes)</h3>
              {doubts.length === 0 && <p className="mt-3 text-sm text-mist">No doubts yet.</p>}
              <ul className="mt-3 max-h-80 space-y-3 overflow-y-auto">
                {doubts.map((d, i) => (
                  <li key={i} className="text-sm">
                    <p><b>{d.student}:</b> {d.question}</p>
                    <p className="mt-1 text-mist">{d.answer}</p>
                  </li>
                ))}
              </ul>
            </div>
          </section>
          <button onClick={() => setData(null)} className="text-sm text-mist underline">Replace with new notes</button>
        </>
      )}
    </div>
  );
}
