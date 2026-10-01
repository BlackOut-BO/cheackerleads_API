import { ClipboardDocumentIcon } from "@heroicons/react/24/outline";

import { BaseModal } from "@/shared";
import { copyTextToClipboard } from "@/utils/copyText";

import {
  LeadResult, VERDICT, leadLabel, riskLevel,
} from "./api";


const STATUS_TEXT: Record<string, string> = {
  clean: "ФРЕНДЛИ ЛИД", risky: "РИСКОВАННЫЙ ЛИД", spam: "СПАМ ЛИД", unknown: "НЕ ПРОВЕРЕН",
};

const errOf = (d: Record<string, unknown> | null) => (d && typeof d.error === "string" ? d.error : "Не проверено");

/** Карточка лида — «дружелюбный» формат бота + причины + полный JSON (кнопка «📋 #N»). */
export const LeadDetail = ({ r, onClose }: { r: LeadResult; onClose: () => void }) => {
  const v = VERDICT[r.verdict] || VERDICT.unknown;
  const rows: [string, number | null, Record<string, unknown> | null][] = [
    ["IP адрес", r.ip_score, r.ip_data], ["Email", r.email_score, r.email_data], ["Телефон", r.phone_score, r.phone_data],
  ];
  const social = Object.entries(r.social_data || {}).filter(([, s]) => !s.error);
  const json = JSON.stringify(r, null, 2);

  return (
    <BaseModal header={ `Lead #${r.lead_number}` } containerClasses="sm:max-w-3xl" onClose={ onClose }>
      <div className="space-y-4 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className={ `badge ${v.badge}` }>{ `${v.icon} ${STATUS_TEXT[r.verdict] || r.verdict}` }</span>
          <span className="font-semibold">{ `${(r.verdict || "unknown").toUpperCase()} (оценка: ${(r.final_score ?? 0).toFixed(2)}/100)` }</span>
        </div>
        <div className="font-mono text-xs text-base-content/70 break-all">{ leadLabel(r.lead || {}) }</div>

        <section>
          <h4 className="font-bold">Оценки риска</h4>
          <ul className="mt-1 space-y-0.5">
            { rows.map(([label, s, d]) => (
              <li key={ label }>
                { `• ${label}: ` }
                { s !== null && s !== undefined
                  ? <span className={ riskLevel(s).tone }>{ `${s.toFixed(1)}/100 ${riskLevel(s).text}` }</span>
                  : <span className="text-base-content/60">{ `❌ ${errOf(d)}` }</span> }
              </li>
            )) }
          </ul>
        </section>

        { r.whatsapp_data && (
          <div>
            <span className="font-bold">WhatsApp: </span>
            { r.whatsapp_data.valid ? "✅ Валидный" : "❌ Невалидный" }
            { r.whatsapp_data.error && <span className="text-xs text-base-content/60">{ ` (${r.whatsapp_data.error})` }</span> }
          </div>
        ) }

        { social.length > 0 && (
          <section>
            <h4 className="font-bold">Социальные сети</h4>
            { social.some(([, s]) => s.exists) && <div>{ `✅ Найдено: ${social.filter(([, s]) => s.exists).map(([n]) => n[0].toUpperCase() + n.slice(1)).join(", ")}` }</div> }
            { social.some(([, s]) => !s.exists) && <div>{ `❌ Не найдено: ${social.filter(([, s]) => !s.exists).map(([n]) => n[0].toUpperCase() + n.slice(1)).join(", ")}` }</div> }
          </section>
        ) }

        { r.reasons?.length > 0 && (
          <section>
            <h4 className="font-bold">Reasons</h4>
            <ul className="mt-1 grid gap-x-4 font-mono text-xs sm:grid-cols-2">
              { r.reasons.slice(0, 20).map((x) => <li key={ x } className="break-all">{ `• ${x}` }</li>) }
            </ul>
          </section>
        ) }

        <details>
          <summary className="cursor-pointer font-semibold">JSON</summary>
          <div className="relative mt-2">
            <button type="button" className="btn btn-xs absolute right-2 top-2" onClick={ () => copyTextToClipboard(json) }>
              <ClipboardDocumentIcon className="size-4" /> Копировать
            </button>
            <pre data-json className="max-h-80 overflow-auto rounded-box bg-base-300 p-3 text-xs">{ json }</pre>
          </div>
        </details>
      </div>
    </BaseModal>
  );
};
