import axios from "axios";

import { useUserStore } from "@/store";
import { downloadFile } from "@/utils/download-file";


/**
 * Клиент Buying API для чекера лидов (перенос бота Checkerleads), Swagger: /api/buying/docs.
 * Отдельный axios-инстанс: реальные запросы, демо-мок панели на него не действует.
 */
export const leadsApi = axios.create({ baseURL: "/api/buying/leads", timeout: 60000 });

leadsApi.interceptors.request.use((config) => {
  const userId = useUserStore.getState().currentUserId;
  if (userId) config.headers.set("X-User-Id", String(userId));
  return config;
});

export type Verdict = "clean" | "risky" | "spam" | "unknown";
export type CheckStatus = "cancelled" | "done" | "error" | "queued" | "running";
export interface Lead { email: string | null; ip: string | null; phone: string | null }
export type Stats = Record<Verdict, number>;

export interface LeadResult {
  lead: Partial<Lead>; lead_number: number; verdict: Verdict; final_score: number;
  ip_score: number | null; email_score: number | null; phone_score: number | null;
  ip_data: Record<string, unknown> | null; email_data: Record<string, unknown> | null; phone_data: Record<string, unknown> | null;
  whatsapp_data: { valid?: boolean; error?: string | null } | null;
  social_data: Record<string, { exists?: boolean; error?: string | null }>;
  reasons: string[];
}

export interface Check {
  id: number; user_id: number; source: "file" | "single" | "text"; file_name: string | null; file_type: string | null;
  leads: Partial<Lead>[]; status: CheckStatus; total: number; done: number; results: LeadResult[];
  output_kind: "csv" | "summary" | "txt" | null; output_name: string | null; has_output: boolean;
  message: string | null; error: string | null; created_at: string; finished_at: string | null; stats: Stats;
}

export type CheckListItem = Omit<Check, "has_output" | "leads" | "results">;

export interface Meta {
  welcome: string; help: string; about: string; upload_hint: string; input_hint: string;
  formats: string[]; max_file_mb: number; thresholds: { risky: number; spam: number };
  services: Record<string, boolean>;
}

export interface AuditItem { id: number; user_id: number; action: string; details: Record<string, unknown>; at: string }

export const RUNNING: CheckStatus[] = ["queued", "running"];

export const errorText = (e: unknown): string => {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { detail?: unknown } | undefined;
    if (typeof d?.detail === "string") return d.detail;
    if (Array.isArray(d?.detail)) return (d.detail as { msg: string }[]).map((x) => x.msg).join("; ");
    if (!e.response) return "Сервис чекера лидов недоступен. Попробуй ещё раз чуть позже.";
    return `Ошибка ${e.response.status}`;
  }
  return String(e);
};

export const download = async (path: string, filename: string) => {
  const res = await leadsApi.get(path, { responseType: "blob" });
  const href = URL.createObjectURL(res.data as Blob);
  downloadFile({ downloadUrl: href, downloadName: filename });
  setTimeout(() => URL.revokeObjectURL(href), 1000);
};

export const leadLabel = (l: Partial<Lead>) => [l.ip && `ip=${l.ip}`, l.email && `email=${l.email}`, l.phone && `phone=${l.phone}`]
  .filter(Boolean).join(" | ");

export const VERDICT: Record<Verdict, { label: string; badge: string; icon: string }> = {
  clean: { label: "Clean", badge: "badge-success", icon: "✅" },
  risky: { label: "Risky", badge: "badge-warning", icon: "⚠️" },
  spam: { label: "Spam", badge: "badge-error", icon: "🚫" },
  unknown: { label: "Unknown", badge: "badge-ghost", icon: "❔" },
};

/** «✅ Низкий / ⚠️ Средний / 🚫 Высокий» — как в боте */
export const riskLevel = (s: number) => {
  if (s < 30) return { text: "Низкий", tone: "text-success" };
  if (s < 70) return { text: "Средний", tone: "text-warning" };
  return { text: "Высокий", tone: "text-error" };
};

export const SOURCE_LABEL: Record<Check["source"], string> = { text: "Текст", file: "Файл", single: "Один лид" };
