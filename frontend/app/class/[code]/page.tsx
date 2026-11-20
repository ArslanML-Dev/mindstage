"use client";
import { use, useEffect, useState } from "react";
import SceneView from "@/components/SceneView";
import { api, type AskOut, type LessonOut } from "@/lib/api";
import { useLive, type LiveMessage } from "@/lib/useLive";

export default function StudentView({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const [name, setName] = useState("Student");
  const [data, setData] = useState<LessonOut | null>(null);
  const [scene, setScene] = useState(0);
  const [picked, setPicked] = useState<Record<string, { choice: number; correct?: boolean }>>({});
  const [question, setQuestion] = useState("");
  const [reply, setReply] = useState<AskOut | null>(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => setName(sessionStorage.getItem("mindstage-name") || "Student"), []);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const load = () =>
      api<LessonOut>(`/api/classrooms/${code}/lesson`).then(setData).catch(() => (timer = setTimeout(load, 4000)));
    load();
    return () => clearTimeout(timer);
  }, [code]);

  const onMessage = (m: LiveMessage) => {
    if (m.type === "scene") {
      setScene(m.index);
      api<LessonOut>(`/api/classrooms/${code}/lesson`).then(setData).catch(() => {});
    }
    if (m.type === "answer_result")
      setPicked((p) => ({ ...p, [`${m.scene}-${m.question}`]: { ...p[`${m.scene}-${m.question}`], correct: m.correct } }));
  };
  const { connected, send } = useLive(code, `role=student&name=${encodeURIComponent(name)}`, onMessage);

  function answer(qi: number, choice: number) {
    const key = `${scene}-${qi}`;
    if (picked[key]) return;
    setPicked((p) => ({ ...p, [key]: { choice } }));
    send({ type: "answer", scene, question: qi, choice });
  }

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    setAsking(true);
    setError("");
    try {
      setReply(await api<AskOut>(`/api/classrooms/${code}/ask`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student: name, question }),
      }));
      setQuestion("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAsking(false);
    }
  }

  const lesson = data?.lesson;
  if (!lesson) {
    return (
      <div className="mt-20 text-center">
        <p className="font-display text-3xl">Waiting for your teacher to start the lesson…</p>
        <p className="mt-3 text-mist">Class {code} · {connected ? "connected" : "connecting"}</p>
      </div>
    );
  }
  const current = lesson.scenes[Math.min(scene, lesson.scenes.length - 1)];

  return (
    <div className="space-y-8">
      <p className="text-sm text-mist">{lesson.topic} · class {code} · {connected ? "● live" : "○ reconnecting"}</p>
      <SceneView scene={current} index={scene} total={lesson.scenes.length} />

      <section className="rounded-2xl border border-line bg-panel p-5">
        <h3 className="font-semibold">Checkpoint</h3>
        {current.mcqs.map((q, qi) => {
          const p = picked[`${scene}-${qi}`];
          return (
            <div key={qi} className="mt-4">
              <p>{q.question}</p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {q.options.map((o, oi) => {
                  const chosen = p?.choice === oi;
                  const tone = !p ? "border-line hover:border-gold"
                    : oi === q.answer_index ? "border-gold bg-gold/10"
                    : chosen ? "border-red-400 bg-red-400/10" : "border-line opacity-60";
                  return (
                    <button key={oi} onClick={() => answer(qi, oi)} disabled={!!p}
                      className={`rounded-lg border px-4 py-2 text-left text-sm ${tone}`}>{o}</button>
                  );
                })}
              </div>
              {p && <p className="mt-2 text-sm text-mist">{p.correct === false ? "Not quite. " : p.correct ? "Correct! " : ""}{q.why}</p>}
            </div>
          );
        })}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={ask} className="rounded-2xl border border-line bg-panel p-5">
          <h3 className="font-semibold">Ask a doubt</h3>
          <p className="text-xs text-mist">Answered only from your teacher&apos;s notes.</p>
          <div className="mt-3 flex gap-2">
            <input value={question} onChange={(e) => setQuestion(e.target.value)} minLength={3} required
              placeholder="e.g. Why does the rate stop increasing?"
              className="flex-1 rounded-lg border border-line bg-ink px-3 py-2 outline-none focus:border-gold" />
            <button disabled={asking} className="rounded-full bg-gold px-4 font-semibold text-ink disabled:opacity-60">
              {asking ? "…" : "Ask"}
            </button>
          </div>
          {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
          {reply && (
            <div className="mt-4 space-y-2 text-sm">
              <p>{reply.answer}</p>
              <details className="text-mist">
                <summary className="cursor-pointer">Sources from the notes ({reply.sources.length})</summary>
                <ol className="mt-2 list-decimal space-y-2 pl-5">
                  {reply.sources.map((s) => <li key={s.position}>{s.text}…</li>)}
                </ol>
              </details>
            </div>
          )}
        </form>
        <div className="rounded-2xl border border-line bg-panel p-5">
          <h3 className="font-semibold">Your notes for this lesson</h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[#d6dbe4]">
            {lesson.summary_notes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        </div>
      </section>
    </div>
  );
}
