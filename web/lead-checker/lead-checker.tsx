import { useCallback, useEffect, useState } from "react";
import { InformationCircleIcon, QuestionMarkCircleIcon } from "@heroicons/react/24/outline";
import { toast } from "react-toastify";

import { BaseModal, EmptyScreen } from "@/shared";

import { Panel, TabsBox } from "../../kit";
import { usePoll } from "../celeb-search/use-poll";
import {
  Check, Meta, RUNNING, errorText, leadsApi,
} from "./api";
import { NewCheck } from "./new-check";
import { CheckResult } from "./check-result";
import { History } from "./history";
import { Audit } from "./audit";


type Tab = "audit" | "check" | "history";
const ACTIVE_KEY = "hubLeadsActiveCheck";

/**
 * Чекер лидов — перенос бота Checkerleads (@cheackerleadsbot) в веб.
 * Тот же флоу: ✍️ Ввести данные / 📤 Загрузить файл → проверка email, IP, телефона, WhatsApp и соцсетей →
 * оценка риска и вердикт clean / risky / spam → файл с результатами и «📋 #N» по каждому лиду.
 */
export const LeadChecker = () => {
  const [tab, setTab] = useState<Tab>("check");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [check, setCheck] = useState<Check | null>(null);
  const [modal, setModal] = useState<"about" | "help" | null>(null);
  const [historyKey, setHistoryKey] = useState(0);

  const remember = (c: Check | null) => {
    setCheck(c);
    try {
      if (c) sessionStorage.setItem(ACTIVE_KEY, String(c.id));
      else sessionStorage.removeItem(ACTIVE_KEY);
    } catch { /* приватный режим */ }
  };

  useEffect(() => {
    leadsApi.get<Meta>("/meta").then((r) => setMeta(r.data)).catch((e) => toast.error(errorText(e)));
    let id: string | null = null;
    try { id = sessionStorage.getItem(ACTIVE_KEY); } catch { /* приватный режим */ }
    if (id) leadsApi.get<Check>(`/checks/${id}`).then((r) => setCheck(r.data)).catch(() => undefined);
  }, []);

  const running = !!check && RUNNING.includes(check.status);
  const refresh = useCallback(async () => {
    if (!check) return;
    const r = (await leadsApi.get<Check>(`/checks/${check.id}`)).data;
    setCheck(r);
    if (!RUNNING.includes(r.status)) {
      setHistoryKey((k) => k + 1);
      if (r.status === "done") toast.success(`Проверка #${r.id} готова: ${r.results.length} лидов`);
    }
  }, [check]);
  usePoll(refresh, 1500, running);

  const open = async (id: number) => {
    try {
      remember((await leadsApi.get<Check>(`/checks/${id}`)).data);
      setTab("check");
    } catch (e) {
      toast.error(errorText(e));
    }
  };
  const retry = async (id: number) => {
    try {
      remember((await leadsApi.post<Check>(`/checks/${id}/retry`)).data);
      setTab("check");
    } catch (e) {
      toast.error(errorText(e));
    }
  };
  const cancel = async () => {
    if (!check) return;
    try {
      await leadsApi.post(`/checks/${check.id}/cancel`);
      await refresh();
      toast.info("Проверка остановлена");
    } catch (e) {
      toast.error(errorText(e));
    }
  };

  if (!meta) return <div className="skeleton h-64 w-full" />;
  const offline = Object.entries(meta.services).filter(([, ok]) => !ok).map(([n]) => n);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <TabsBox<Tab> value={ tab } tabs={ [{ id: "check", label: "Проверка" }, { id: "history", label: "История" }, { id: "audit", label: "Журнал действий" }] } onChange={ setTab } />
        <div className="ml-auto flex gap-1">
          <button type="button" className="btn btn-sm btn-ghost gap-1" onClick={ () => setModal("help") }><QuestionMarkCircleIcon className="size-5" /> Справка</button>
          <button type="button" className="btn btn-sm btn-ghost gap-1" onClick={ () => setModal("about") }><InformationCircleIcon className="size-5" /> О боте</button>
        </div>
      </div>

      { tab === "check" && offline.length > 0 && (
        <div role="alert" className="alert alert-warning alert-soft text-sm">
          { `Не настроены ключи: ${offline.join(", ")}. Эти проверки вернут «API key not configured» — как бот без ключей; итоговая оценка считается по остальным.` }
        </div>
      ) }

      { tab === "check" && (
        <div className="grid gap-4 lg:grid-cols-3">
          <NewCheck busy={ running } meta={ meta } onStarted={ (c) => { remember(c); setHistoryKey((k) => k + 1); } } />
          { check
            ? <CheckResult check={ check } onCancel={ cancel } onNew={ () => remember(null) } onRetry={ () => retry(check.id) } />
            : (
              <Panel title="Результат" className="lg:col-span-2">
                <EmptyScreen icon={ <InformationCircleIcon /> } iconSize="sm">
                  <p className="whitespace-pre-line text-left text-sm text-base-content/70">{ meta.welcome }</p>
                </EmptyScreen>
              </Panel>
            ) }
        </div>
      ) }
      { tab === "history" && <History reloadKey={ historyKey } onOpen={ open } onRetry={ retry } /> }
      { tab === "audit" && <Audit /> }

      { modal && (
        <BaseModal header={ modal === "help" ? "📖 Справка" : "ℹ️ О боте Checkerleads" } containerClasses="sm:max-w-2xl" onClose={ () => setModal(null) }>
          <p className="whitespace-pre-line text-sm">{ modal === "help" ? meta.help : meta.about }</p>
        </BaseModal>
      ) }
    </div>
  );
};
