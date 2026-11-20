export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const WS_URL = API_URL.replace(/^http/, "ws");

export type FlowNode = { id: string; label: string };
export type FlowEdge = { from: string; to: string; label?: string };
export type Visual =
  | { type: "flowchart"; nodes: FlowNode[]; edges: FlowEdge[] }
  | { type: "chart"; chart_type: "bar" | "line"; title: string; labels: string[]; values: number[]; unit: string }
  | { type: "keyfacts"; facts: { emoji: string; text: string }[] }
  | { type: "slider"; label: string; unit: string; min: number; max: number; value: number; formula: string;
      result_label: string; result_unit: string };
export type MCQ = { question: string; options: string[]; answer_index: number; why: string };
export type Scene = { title: string; story: string; analogy: string; visual: Visual; mcqs: MCQ[] };
export type Lesson = { topic: string; scenes: Scene[]; summary_notes: string[] };
export type LessonOut = { code: string; engine: string; lesson: Lesson; chunks_indexed: number };
export type AskOut = { answer: string; sources: { position: number; text: string; score: number }[] };

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  return body as T;
}

export const tokenKey = (code: string) => `mindstage-teacher-${code}`;
