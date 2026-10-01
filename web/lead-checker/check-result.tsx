import { useState } from "react";
import {
  ArrowDownTrayIcon, ArrowPathIcon, PlusIcon, StopIcon,
} from "@heroicons/react/24/outline";
import { toast } from "react-toastify";

import { twClassNames } from "@/utils";

import {
  DataTable, FilterChips, Panel, Progress,
} from "../../kit";
import {
  Check, LeadResult, RUNNING, SOURCE_LABEL, VERDICT, Verdict, download, errorText, leadLabel,
} from "./api";
import { LeadDetail } from "./lead-detail";


type Filter = Verdict | "all";
const ORDER: Record<string, number> = {
  spam: 0, risky: 1, clean: 2, unknown: 3,
};
const STATUS_BADGE: Record<string, string> = {
  done: "badge-success", error: "badge-error", cancelled: "badge-ghost", queued: "badge-info", running: "badge-info",
};
const STATUS_LABEL: Record<string, string> = {
  queued: "В очереди", running: "Проверяю…", done: "Готово", error: "Ошибка", cancelled: "Отменено",
};

const scoreCell = (s: number | null) => (s === null || s === undefined ? <span className="text-base-content/40">N/A</span> : s.toFixed(1));

/** Результат проверки — то, что бот присылал в чат: файл, сводка SPAM → RISKY → CLEAN и «📋 #N». */
export const CheckResult = ({
  check, onCancel, onRetry, onNew,
}: { check: Check; onCancel: () => void; onRetry: () => void; onNew: () => void }) => {
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<LeadResult | null>(null);
  const running = RUNNING.includes(check.status);
  const results = [...(check.results || [])].sort((a, b) => (ORDER[a.verdict] ?? 9) - (ORDER[b.verdict] ?? 9) || a.lead_number - b.lead_number);
  const shown = filter === "all" ? results : results.filter((r) => r.verdict === filter);
  const dl = (path: string, name: string) => download(path, name).catch((e) => toast.error(errorText(e)));

  return (
    <Panel
      className="lg:col-span-2"
      title={ (
        <span className="flex flex-wrap items-center gap-2">
          { `Проверка #${check.id}` }
          <span className="font-normal text-base-content/60">{ `· ${SOURCE_LABEL[check.source]}${check.file_name ? `: ${check.file_name}` : ""}` }</span>
          <span className={ twClassNames("badge badge-soft", STATUS_BADGE[check.status]) } data-status={ check.status }>{ STATUS_LABEL[check.status] }</span>
        </span>
      ) }
      action={ (
        <div className="flex flex-wrap gap-2">
          { running && <button type="button" className="btn btn-sm btn-ghost bg-base-300" onClick={ onCancel }><StopIcon className="size-4" /> Остановить</button> }
          { !running && <button type="button" className="btn btn-sm btn-ghost bg-base-300" onClick={ onRetry }><ArrowPathIcon className="size-4" /> Проверить ещё раз</button> }
          { !running && <button type="button" className="btn btn-sm btn-ghost" onClick={ onNew }><PlusIcon className="size-4" /> Новая</button> }
        </div>
      ) }
    >
      { check.message && <p className="whitespace-pre-line text-sm">{ check.message }</p> }
      { running && <Progress done={ check.done } total={ check.total } label="Проверено лидов" /> }
      { check.status === "error" && <div role="alert" className="alert alert-error alert-soft text-sm">{ check.error }</div> }

      { check.status === "done" && (
        <>
          <div className="stats stats-horizontal w-full border border-base-300 bg-base-100">
            <div className="stat py-3"><div className="stat-title">Всего</div><div className="stat-value text-2xl">{ results.length }</div></div>
            <div className="stat py-3"><div className="stat-title">✅ Clean</div><div className="stat-value text-2xl text-success">{ check.stats.clean }</div></div>
            <div className="stat py-3"><div className="stat-title">⚠️ Risky</div><div className="stat-value text-2xl text-warning">{ check.stats.risky }</div></div>
            <div className="stat py-3"><div className="stat-title">🚫 Spam</div><div className="stat-value text-2xl text-error">{ check.stats.spam }</div></div>
          </div>

          <div className="flex flex-wrap gap-2">
            { check.has_output && check.output_name && (
              <button type="button" className="btn btn-sm btn-primary" onClick={ () => dl(`/checks/${check.id}/download`, check.output_name as string) }>
                <ArrowDownTrayIcon className="size-4" /> { check.output_name }
              </button>
            ) }
            <button type="button" className="btn btn-sm btn-ghost bg-base-300" onClick={ () => dl(`/checks/${check.id}/export.csv`, `leads_check_${check.id}.csv`) }>CSV</button>
            <button type="button" className="btn btn-sm btn-ghost bg-base-300" onClick={ () => dl(`/checks/${check.id}/export.json`, `leads_check_${check.id}.json`) }>JSON</button>
          </div>

          <DataTable
            instant
            searchable
            rows={ shown }
            rowKey={ (r) => r.lead_number }
            empty="В этой группе лидов нет"
            toolbar={ (
              <FilterChips<Filter>
                value={ filter }
                items={ [
                  { id: "all", label: "Все", count: results.length },
                  {
                    id: "spam", label: "🚫 Spam", count: check.stats.spam, tone: "badge-error",
                  },
                  {
                    id: "risky", label: "⚠️ Risky", count: check.stats.risky, tone: "badge-warning",
                  },
                  {
                    id: "clean", label: "✅ Clean", count: check.stats.clean, tone: "badge-success",
                  },
                ] }
                onChange={ setFilter }
              />
            ) }
            cols={ [
              {
                key: "n", label: "#", value: (r) => r.lead_number, render: (r) => <span className="text-base-content/50">{ r.lead_number }</span>,
              },
              {
                key: "lead", label: "Лид", value: (r) => leadLabel(r.lead || {}), render: (r) => <span className="font-mono text-xs break-all">{ leadLabel(r.lead || {}) }</span>,
              },
              {
                key: "v",
                label: "Вердикт",
                value: (r) => r.final_score ?? 0,
                render: (r) => {
                  const v = VERDICT[r.verdict] || VERDICT.unknown;
                  return <span className={ `badge badge-soft badge-sm ${v.badge}` }>{ `${v.label} · ${(r.final_score ?? 0).toFixed(1)}` }</span>;
                },
              },
              {
                key: "ip", label: "IP", value: (r) => r.ip_score ?? -1, render: (r) => scoreCell(r.ip_score),
              },
              {
                key: "em", label: "Email", value: (r) => r.email_score ?? -1, render: (r) => scoreCell(r.email_score),
              },
              {
                key: "ph", label: "Тел.", value: (r) => r.phone_score ?? -1, render: (r) => scoreCell(r.phone_score),
              },
              {
                key: "wa",
                label: "WA",
                render: (r) => {
                  if (!r.whatsapp_data) return <span className="text-base-content/40">—</span>;
                  return r.whatsapp_data.valid ? "✅" : "❌";
                },
              },
              {
                key: "d",
                label: "",
                render: (r) => <button type="button" className="btn btn-xs btn-ghost bg-base-300" onClick={ () => setOpen(r) }>{ `📋 #${r.lead_number}` }</button>,
              },
            ] }
          />
        </>
      ) }
      { open && <LeadDetail r={ open } onClose={ () => setOpen(null) } /> }
    </Panel>
  );
};
