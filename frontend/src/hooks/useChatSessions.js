import { useCallback, useEffect, useRef, useState } from "react";
import { api, newSessionId } from "../api.js";

function makeSession() {
  const day = new Date();
  day.setDate(day.getDate() + 1);
  return {
    id: newSessionId(),
    title: "Cuộc trò chuyện mới",
    createdAt: Date.now(),
    date: `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`,
    lang: "vi",
    messages: [],
    plan: null,
    draft: "",
    loading: false,
    error: null,
    weather: null,
    selectedPoi: null,
    selection: null,
    tab: "trip",
    mobilePane: "chat",
  };
}

export default function useChatSessions() {
  const [store, setStore] = useState(() => {
    const session = makeSession();
    return { activeId: session.id, sessions: [session] };
  });
  const snapshot = useRef(store);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const commit = useCallback((updater) => {
    if (!alive.current) return;
    snapshot.current = updater(snapshot.current);
    setStore(snapshot.current);
  }, []);
  const patch = useCallback(
    (id, changes) =>
      commit((current) => ({
        ...current,
        sessions: current.sessions.map((session) =>
          session.id === id
            ? {
                ...session,
                ...(typeof changes === "function" ? changes(session) : changes),
              }
            : session,
        ),
      })),
    [commit],
  );
  const createSession = useCallback(() => {
    const session = makeSession();
    commit((current) => ({
      activeId: session.id,
      sessions: [session, ...current.sessions],
    }));
    return session.id;
  }, [commit]);
  const switchSession = useCallback(
    (id) =>
      commit((current) =>
        current.sessions.some((session) => session.id === id)
          ? { ...current, activeId: id }
          : current,
      ),
    [commit],
  );
  const setField = useCallback(
    (name, value) =>
      patch(snapshot.current.activeId, (session) => ({
        [name]: typeof value === "function" ? value(session[name]) : value,
      })),
    [patch],
  );
  const send = useCallback(
    async (text, retry = false, targetId = snapshot.current.activeId) => {
      const session = snapshot.current.sessions.find(
        (item) => item.id === targetId,
      );
      if (!session || session.loading || (retry && !session.error))
        return false;
      const requestDate = retry ? session.error.date : session.date;
      patch(targetId, {
        loading: true,
        error: null,
        draft: "",
        selectedPoi: null,
        selection: null,
        messages: retry
          ? session.messages
          : [...session.messages, { role: "user", content: text }],
        title: session.messages.length ? session.title : text.slice(0, 46),
      });
      try {
        const result = await api.chat(targetId, text, requestDate);
        if (typeof result?.reply !== "string" || !result.reply.trim())
          throw new Error(
            "Máy chủ chưa trả về nội dung phản hồi. Vui lòng thử lại.",
          );
        patch(targetId, (current) => ({
          messages: [
            ...current.messages,
            { role: "assistant", content: result.reply },
          ],
          plan: result.plan ?? null,
          weather: result.weather ?? current.weather,
        }));
      } catch (error) {
        patch(targetId, {
          error: { text, date: requestDate, message: error.message },
        });
      } finally {
        patch(targetId, { loading: false });
      }
      return true;
    },
    [patch],
  );
  return {
    sessions: store.sessions,
    active: store.sessions.find((session) => session.id === store.activeId),
    createSession,
    switchSession,
    setField,
    patch,
    send,
  };
}
