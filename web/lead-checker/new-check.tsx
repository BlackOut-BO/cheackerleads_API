import {
  DragEvent, useEffect, useRef, useState,
} from "react";
import { ArrowUpTrayIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { toast } from "react-toastify";

import { twClassNames } from "@/utils";

import { Panel } from "../../kit";
import {
  Check, Lead, Meta, errorText, leadLabel, leadsApi,
} from "./api";


type Mode = "file" | "single" | "text";

interface Preview { count: number; leads: Partial<Lead>[]; error: string | null; columns?: string[]; is_table?: boolean }

const SAMPLE = "email=test@example.com | ip=8.8.8.8 | phone=+14155552671\nuser@gmail.com 1.1.1.1 +491511234567";

/** Как кнопки бота «✍️ Ввести данные» и «📤 Загрузить файл» (+ отдельные поля для одного лида). */
export const NewCheck = ({ meta, busy, onStarted }: { meta: Meta; busy: boolean; onStarted: (c: Check) => void }) => {
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [single, setSingle] = useState<Lead>({ email: "", ip: "", phone: "" });
  const [preview, setPreview] = useState<Preview | null>(null);
  const [drag, setDrag] = useState(false);
  const [sending, setSending] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  // предпросмотр распознавания — без проверки и без трат на API
  useEffect(() => {
    if (mode !== "text") return undefined;
    if (!text.trim()) { setPreview(null); return undefined; }
    const t = setTimeout(() => {
      leadsApi.post<Preview>("/parse/text", { text }).then((r) => setPreview(r.data)).catch(() => setPreview(null));
    }, 350);
    return () => clearTimeout(t);
  }, [text, mode]);

  const pickFile = async (f?: File | null) => {
    if (!f) return;
    setFile(f);
    setPreview(null);
    const fd = new FormData();
    fd.append("file", f);
    try {
      setPreview((await leadsApi.post<Preview>("/parse/file", fd)).data);
    } catch (e) {
      setPreview({ count: 0, leads: [], error: errorText(e) });
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    setMode("file");
    pickFile(e.dataTransfer.files[0]);
  };

  const start = async () => {
    setSending(true);
    try {
      let r;
      if (mode === "text") r = await leadsApi.post<Check>("/checks/text", { text });
      else if (mode === "single") r = await leadsApi.post<Check>("/checks/single", single);
      else {
        const fd = new FormData();
        fd.append("file", file as File);
        r = await leadsApi.post<Check>("/checks/file", fd);
      }
      onStarted(r.data);
    } catch (e) {
      toast.error(errorText(e));
    } finally {
      setSending(false);
    }
  };

  const singleOk = !!(single.email?.trim() || single.ip?.trim() || single.phone?.trim());
  const ready = (mode === "text" && !!preview?.count) || (mode === "file" && !!file && !!preview?.count) || (mode === "single" && singleOk);
  const tab = (m: Mode) => twClassNames("btn btn-sm join-item", mode === m ? "btn-primary" : "bg-base-300");

  return (
    <Panel
      title="Новая проверка"
      action={ mode === "text" && <button type="button" className="btn btn-xs btn-ghost" onClick={ () => setText(SAMPLE) }>Пример</button> }
    >
      <div className="join w-full">
        <button type="button" className={ tab("text") } onClick={ () => { setMode("text"); setPreview(null); } }>✍️ Ввести данные</button>
        <button type="button" className={ tab("file") } onClick={ () => { setMode("file"); setPreview(null); setFile(null); } }>📤 Файл</button>
        <button type="button" className={ tab("single") } onClick={ () => setMode("single") }>Один лид</button>
      </div>

      { mode === "text" && (
        <div
          className={ twClassNames("rounded-box transition", { "ring-2 ring-primary ring-offset-2 ring-offset-base-200": drag }) }
          onDragOver={ (e) => { e.preventDefault(); setDrag(true); } }
          onDragLeave={ () => setDrag(false) }
          onDrop={ onDrop }
        >
          <textarea
            rows={ 8 }
            className="textarea w-full font-mono text-xs"
            aria-label="Лиды"
            placeholder={ meta.input_hint }
            value={ text }
            onChange={ (e) => setText(e.target.value) }
          />
        </div>
      ) }

      { mode === "file" && (
        <button
          type="button"
          className={ twClassNames(
            "flex w-full flex-col items-center gap-2 rounded-box border-2 border-dashed p-6 text-center transition",
            drag ? "border-primary bg-primary/10" : "border-base-300 hover:border-primary/50",
          ) }
          onClick={ () => input.current?.click() }
          onDragOver={ (e) => { e.preventDefault(); setDrag(true); } }
          onDragLeave={ () => setDrag(false) }
          onDrop={ onDrop }
        >
          <ArrowUpTrayIcon className="size-7 text-primary" />
          <span className="font-semibold">{ file ? file.name : "Выбрать или перетащить файл" }</span>
          <span className="text-xs text-base-content/60">{ `${meta.formats.join(", ")} · до ${meta.max_file_mb} МБ` }</span>
          <input ref={ input } hidden type="file" aria-label="Файл с лидами" accept={ meta.formats.join(",") } onChange={ (e) => pickFile(e.target.files?.[0]) } />
        </button>
      ) }

      { mode === "single" && (
        <div className="space-y-2">
          { (["email", "ip", "phone"] as const).map((k) => (
            <input
              key={ k }
              className="input input-sm w-full"
              aria-label={ k }
              placeholder={{ email: "Email — test@example.com", ip: "IP — 8.8.8.8", phone: "Телефон — +14155552671" }[k]}
              value={ single[k] || "" }
              onChange={ (e) => setSingle({ ...single, [k]: e.target.value }) }
            />
          )) }
          <p className="text-xs text-base-content/60">Достаточно одного поля. Соцсети проверяются по email, WhatsApp — по телефону.</p>
        </div>
      ) }

      { preview && mode !== "single" && (
        <div className={ twClassNames("rounded-box p-3 text-sm", preview.count ? "bg-base-300" : "bg-error/10 text-error") }>
          { preview.count ? (
            <>
              <div className="font-semibold">
                { `${mode === "file" ? "Найдено" : "Распознано"} лидов: ${preview.count}` }
                { preview.columns?.length ? <span className="font-normal text-base-content/60">{ ` · колонки: ${preview.columns.join(", ")}` }</span> : null }
              </div>
              <ul className="mt-1 max-h-32 space-y-0.5 overflow-auto font-mono text-xs text-base-content/70">
                { preview.leads.slice(0, 50).map((l, i) => <li key={ `${i + 1}-${leadLabel(l)}` }>{ `${i + 1}. ${leadLabel(l)}` }</li>) }
              </ul>
            </>
          ) : <span className="whitespace-pre-line">{ preview.error }</span> }
        </div>
      ) }

      <button type="button" className="btn btn-primary w-full" disabled={ !ready || sending || busy } onClick={ start }>
        { sending ? <span className="loading loading-spinner loading-sm" /> : <MagnifyingGlassIcon className="size-4" /> }
        Проверить
      </button>
    </Panel>
  );
};
