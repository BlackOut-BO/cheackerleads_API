import { useEffect, useState } from "react";
import { toast } from "react-toastify";

import { DataTable, Panel } from "../../kit";
import { AuditItem, errorText, leadsApi } from "./api";


const ACTION: Record<string, string> = {
  "check.start": "Запуск проверки",
  "check.done": "Проверка завершена",
  "check.error": "Ошибка проверки",
  "check.cancel": "Остановка",
  "check.retry": "Повтор",
  "check.delete": "Удаление",
  "check.download": "Скачивание файла",
  "check.export": "Выгрузка",
  "tool.email": "Проверка email",
  "tool.ip": "Проверка IP",
  "tool.phone": "Проверка телефона",
  "tool.whatsapp": "Проверка WhatsApp",
  "tool.social": "Проверка соцсетей",
};

/** Журнал действий: кто, что, когда. Админ (LEADS_ADMIN_IDS) может смотреть действия всех пользователей. */
export const Audit = () => {
  const [items, setItems] = useState<AuditItem[] | null>(null);
  const [admin, setAdmin] = useState(false);
  const [all, setAll] = useState(false);

  useEffect(() => {
    leadsApi.get<{ is_admin: boolean; items: AuditItem[] }>("/audit", { params: { all_users: all || undefined, limit: 200 } })
      .then((r) => { setItems(r.data.items); setAdmin(r.data.is_admin); })
      .catch((e) => toast.error(errorText(e)));
  }, [all]);

  return (
    <Panel
      title="Журнал действий"
      action={ admin && (
        <label htmlFor="leads-audit-all" className="flex cursor-pointer items-center gap-2 text-sm">
          <input id="leads-audit-all" type="checkbox" className="toggle toggle-sm toggle-primary" checked={ all } onChange={ (e) => setAll(e.target.checked) } />
          Все пользователи
        </label>
      ) }
    >
      { items === null ? <div className="skeleton h-24 w-full" /> : (
        <DataTable
          instant
          searchable
          exportName="leads-audit"
          rows={ items }
          rowKey={ (r) => r.id }
          empty="Действий пока нет"
          cols={ [
            {
              key: "t", label: "Когда", value: (r) => r.at, render: (r) => <span className="whitespace-nowrap text-xs">{ new Date(r.at).toLocaleString("ru-RU") }</span>,
            },
            {
              key: "u", label: "Кто", value: (r) => r.user_id, render: (r) => `#${r.user_id}`,
            },
            {
              key: "a", label: "Действие", value: (r) => ACTION[r.action] || r.action, render: (r) => ACTION[r.action] || r.action,
            },
            {
              key: "d",
              label: "Детали",
              value: (r) => JSON.stringify(r.details),
              render: (r) => (
                <span className="font-mono text-xs text-base-content/70 break-all">
                  { Object.entries(r.details).map(([k, v]) => `${k}=${String(v)}`).join(" · ") }
                </span>
              ),
            },
          ] }
        />
      ) }
    </Panel>
  );
};
