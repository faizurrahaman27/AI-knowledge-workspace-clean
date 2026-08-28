import { useState, useEffect, useRef } from "react";
import { Send, Bookmark } from "lucide-react";
import api, { API_BASE_URL } from "../api/axios";

// fetch() bypasses api/axios.js's interceptors, so an expired access token
// would otherwise just fail here instead of silently refreshing like every
// other axios-based call in the app. This mirrors that same refresh-once
// behavior for this one streaming request.
async function streamingChatFetch(payload, isRetry = false) {
  const token = localStorage.getItem("token");

  const res = await fetch(`${API_BASE_URL}/chat/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (res.status === 401 && !isRetry) {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return res;

    try {
      const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!refreshRes.ok) return res;

      const data = await refreshRes.json();
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      return streamingChatFetch(payload, true);
    } catch {
      return res;
    }
  }

  return res;
}

export default function ChatPanel({
  selectedDocument = null,
  workspace = null,
  prefillQuestion = null,
  onPrefillConsumed = () => {},
  onCitationClick = () => {},
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
  }, [input]);

  // Text selected in the PDF viewer arrives here via Dashboard's
  // pendingQuestion state, prefilled and ready to send.
  useEffect(() => {
    if (prefillQuestion) {
      setInput(prefillQuestion);
      onPrefillConsumed();
      setTimeout(() => textareaRef.current?.focus(), 0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefillQuestion]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = {
      id: "m_" + Date.now(),
      sender: "user",
      text: input,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    const promptText = input;
    setInput("");
    setLoading(true);

    const botId = "m_bot_" + Date.now();
    setMessages((prev) => [
      ...prev,
      {
        id: botId,
        sender: "bot",
        text: "",
        citations: [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);

    try {
      const payload = {
        question: promptText,
        document_id: selectedDocument?.id ?? null,
        workspace_id: workspace?.id ?? null,
        explain_level: null,
        want_translation: true,
      };

      const res = await streamingChatFetch(payload);

      if (!res.ok || !res.body) {
        const bodyText = await res.text().catch(() => "");
        throw new Error(`Request failed (${res.status}): ${bodyText || res.statusText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          let chunk;
          try {
            chunk = JSON.parse(trimmed);
          } catch {
            continue;
          }

          // ADJUST THESE FIELD NAMES to whatever chat_service.py actually yields.
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== botId) return m;
              return {
                ...m,
                text: m.text + (chunk.token ?? chunk.answer ?? chunk.text ?? ""),
                citations: Array.isArray(chunk.citations) ? chunk.citations : m.citations,
              };
            })
          );
        }
      }
    } catch (err) {
      console.error("Chat request failed:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botId
            ? { ...m, text: `Something went wrong: ${err.message || "please try again."}` }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-full overflow-hidden bg-[#FAF9F5] rounded-xl">
      <div className="flex-1 flex flex-col min-w-0">
        {isEmpty ? (
          <div className="flex-1 flex flex-col items-center justify-center px-6">
            <div className="w-full max-w-2xl">
              <h1
                className="text-[24px] leading-tight text-[#3D3D3A] mb-6 text-center"
                style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
              >
                {workspace ? `Ask about ${workspace.name}` : selectedDocument ? `Ask about ${selectedDocument.filename}` : "What would you like to know?"}
              </h1>
              <ComposerBar
                input={input}
                setInput={setInput}
                onSend={handleSend}
                onKeyDown={handleKeyDown}
                loading={loading}
                textareaRef={textareaRef}
              />
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
                {messages.map((m) => (
                  <div key={m.id} className={m.sender === "user" ? "flex justify-end" : ""}>
                    {m.sender === "user" ? (
                      <div className="max-w-[75%] bg-[#F0EEE6] text-[#3D3D3A] text-[14px] leading-relaxed rounded-2xl px-4 py-3">
                        {m.text}
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <div className="text-[14px] leading-relaxed text-[#3D3D3A] whitespace-pre-wrap">
                          {m.text}
                        </div>

                        {Array.isArray(m.citations) && m.citations.length > 0 && (
                          <div className="space-y-1.5 pt-1">
                            <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#8C8A80] uppercase tracking-wide">
                              <Bookmark className="w-3 h-3" />
                              Sources
                            </div>
                            <div className="grid sm:grid-cols-2 gap-2">
                              {m.citations.map((c, idx) => (
                                <button
                                  key={idx}
                                  onClick={() => onCitationClick(c.page, c.snippet || c.excerpt || c.text_snippet)}
                                  className="text-left bg-white border border-[#E8E6DD] rounded-xl px-3 py-2.5 border-l-2 border-l-[#C2694B] hover:bg-[#F5F3EC] transition"
                                >
                                  <div className="flex items-center justify-between text-[12px] font-medium text-[#3D3D3A]">
                                    <span className="truncate">{c.filename || c.source || c.document_name}</span>
                                    <span className="text-[10px] text-[#A6A499] shrink-0 ml-2">p.{c.page}</span>
                                  </div>
                                  <div className="text-[11px] text-[#8C8A80] mt-1 italic line-clamp-2">
                                    {c.snippet || c.excerpt || c.text_snippet}
                                  </div>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="flex items-center gap-2 text-[13px] text-[#8C8A80]">
                    <span className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#C2694B] animate-bounce [animation-delay:-0.3s]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-[#C2694B] animate-bounce [animation-delay:-0.15s]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-[#C2694B] animate-bounce" />
                    </span>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>
            </div>

            <div className="border-t border-[#E8E6DD] bg-[#FAF9F5] px-6 py-4">
              <div className="max-w-3xl mx-auto">
                <ComposerBar
                  input={input}
                  setInput={setInput}
                  onSend={handleSend}
                  onKeyDown={handleKeyDown}
                  loading={loading}
                  textareaRef={textareaRef}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ComposerBar({ input, setInput, onSend, onKeyDown, loading, textareaRef }) {
  return (
    <form
      onSubmit={onSend}
      className="bg-white border border-[#E8E6DD] rounded-2xl shadow-sm focus-within:border-[#C2694B]/50 focus-within:ring-2 focus-within:ring-[#C2694B]/10 transition flex items-end gap-2 px-4 py-3"
    >
      <textarea
        ref={textareaRef}
        rows={1}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask about your documents..."
        className="flex-1 resize-none bg-transparent text-[14px] text-[#3D3D3A] placeholder-[#A6A499] focus:outline-none max-h-48 leading-relaxed py-0.5"
      />
      <button
        type="submit"
        disabled={loading || !input.trim()}
        aria-label="Send message"
        className="shrink-0 w-8 h-8 rounded-full bg-[#C2694B] hover:bg-[#B15A3D] disabled:bg-[#E8E6DD] disabled:cursor-not-allowed text-white flex items-center justify-center transition"
      >
        <Send className="w-3.5 h-3.5" />
      </button>
    </form>
  );
}