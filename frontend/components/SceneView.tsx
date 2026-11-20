import Visual from "./Visual";
import type { Scene } from "@/lib/api";

export default function SceneView({ scene, index, total }: { scene: Scene; index: number; total: number }) {
  return (
    <article key={index} className="scene-in grid gap-8 lg:grid-cols-[1fr_1.3fr]">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-gold">Scene {index + 1} of {total}</p>
        <h2 className="mt-2 font-display text-4xl leading-tight">{scene.title}</h2>
        <p className="mt-5 text-lg leading-relaxed text-[#d6dbe4]">{scene.story}</p>
        {scene.analogy && (
          <p className="mt-5 border-l-2 border-gold pl-4 italic text-mist">Think of it like this: {scene.analogy}</p>
        )}
      </div>
      <div className="rounded-2xl border border-line bg-panel/60 p-5">
        <Visual v={scene.visual} />
      </div>
    </article>
  );
}
