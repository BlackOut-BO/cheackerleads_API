import { useEffect, useState } from "react";
import {
  ArrowDownTrayIcon, ArrowPathIcon, EyeIcon, TrashIcon,
} from "@heroicons/react/24/outline";
import { toast } from "react-toastify";

import { DataTable, Panel } from "../../kit";
import {
  CheckListItem, SOURCE_LABEL, download, errorText, leadsApi,
} from "./api";


const when = (s: string) => new Date(s).toLocaleString("ru-RU");

export const History = ({ onOpen, onRetry, reloadKey }: { onOpen: (id: number) => void; onRetry: (id: number) => void; reloadKey: number }) => {
  const [rows, setRows] = useState<CheckListItem[] | null>(null);
  const load = () => leadsApi.get<CheckListItem[]>("/checks").then((r) => setRows(r.data)).catch((e) => toast.error(errorText(e)));
  useEffect(() => { load(); }, [reloadKey]);

  const remove = async (id: number) => {
    try {
      await leadsApi.delete(`/checks/${id}`);
      setRows((r) => (r || []).filter((x) => x.id !== id));
      toast.success("Проверка удалена из истории");
    } catch (e) {
      toast.error(errorText(e));
    }
  };

  return (
    <Panel title="История проверок">
      { rows === null ? <div className="skeleton h-24 w-full" /> : (
        <DataTable
          instant
          searchable
          rows={ rows }
          rowKey={ (r) => r.id }
          empty="Проверок пока не было"
          cols={ [
            {
              key: "id", label: "#", value: (r) => r.id, render: (r) => r.id,
            },
            {
              key: "src", label: "Источник", value: (r) => `${SOURCE_LABEL[r.source]} ${r.file_name || ""}`, render: (r) => `${SOURCE_LABEL[r.source]}${r.file_name ? `: ${r.file_name}` : ""}`,
            },
            {
              key: "n", label: "Лидов", value: (r) => r.total, render: (r) => r.total,
            },
            {
              key: "s",
              label: "Итог",
              render: (r) => (r.status === "done"
                ? <span className="whitespace-nowrap text-xs">{ `✅ ${r.stats.clean} · ⚠️ ${r.stats.risky} · 🚫 ${r.stats.spam}` }</span>
                : <span className="badge badge-ghost badge-sm">{ r.status }</span>),
            },
            {
              key: "t", label: "Когда", value: (r) => r.created_at, render: (r) => <span className="whitespace-nowrap text-xs">{ when(r.created_at) }</span>,
            },
            {
              key: "a",
              label: "",
              render: (r) => (
                <div className="join">
                  <button type="button" aria-label="Открыть" title="Открыть" className="btn btn-xs btn-ghost join-item" onClick={ () => onOpen(r.id) }><EyeIcon className="size-4" /></button>
                  { r.output_name && (
                    <button type="button" aria-label="Скачать" title={ r.output_name } className="btn btn-xs btn-ghost join-item" onClick={ () => download(`/checks/${r.id}/download`, r.output_name as string).catch((e) => toast.error(errorText(e))) }>
                      <ArrowDownTrayIcon className="size-4" />
                    </button>
                  ) }
                  <button type="button" aria-label="Повторить" title="Проверить ещё раз" className="btn btn-xs btn-ghost join-item" onClick={ () => onRetry(r.id) }><ArrowPathIcon className="size-4" /></button>
                  <button type="button" aria-label="Удалить" title="Удалить" className="btn btn-xs btn-ghost join-item text-error" onClick={ () => remove(r.id) }><TrashIcon className="size-4" /></button>
                </div>
              ),
            },
          ] }
        />
      ) }
    </Panel>
  );
};
