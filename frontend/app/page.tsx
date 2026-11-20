import Link from "next/link";

const steps = [
  ["Upload your notes", "PDF, Word, text or a photo of handwritten notes."],
  ["AI directs the lesson", "Gemini turns them into 4–5 visual scenes with quizzes, checked against a strict schema."],
  ["Teach it live", "Students join with a code; every scene you show appears on their screens instantly."],
  ["Doubts answered from your notes", "Students ask questions; answers come only from your notes (RAG), with sources."],
];

export default function Home() {
  return (
    <div className="space-y-16 py-6">
      <section className="max-w-3xl">
        <p className="text-xs uppercase tracking-[0.3em] text-gold">Education Cinema</p>
        <h1 className="mt-4 font-display text-5xl leading-tight sm:text-6xl">The classroom that becomes anything.</h1>
        <p className="mt-6 text-lg text-mist">
          MindStage turns a teacher&apos;s notes into a live, visual lesson on every student&apos;s screen — so students
          spend the class understanding instead of copying.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/teach" className="rounded-full bg-gold px-6 py-3 font-semibold text-ink hover:brightness-110">
            Start a class
          </Link>
          <Link href="/join" className="rounded-full border border-line px-6 py-3 hover:border-mist">
            Join with a code
          </Link>
        </div>
      </section>
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map(([title, text], i) => (
          <div key={title} className="rounded-2xl border border-line bg-panel p-5">
            <div className="font-display text-3xl text-gold">{i + 1}</div>
            <h3 className="mt-3 font-semibold">{title}</h3>
            <p className="mt-2 text-sm text-mist">{text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
