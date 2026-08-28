import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.mjs?url";
import api from "../api/axios";
import { createAnnotation, listAnnotations, deleteAnnotation } from "../api/annotations";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const RENDER_SCALE = 1.4;
const THUMB_SCALE = 0.2;

function normalize(text) {
  return (text || "").toLowerCase().replace(/\s+/g, " ").trim();
}

// Applies a highlight class to whichever text-layer spans overlap a
// target substring within a page's already-built running text. Used for
// both citation highlighting and search-match highlighting -- same
// underlying problem (find text, highlight the spans that cover it).
function highlightSpans(pageState, targetNormalized, className) {
  if (!pageState || !targetNormalized || targetNormalized.length < 2) return false;

  pageState.spans.forEach(({ span }) => span.classList.remove(className));

  const normalizedFull = normalize(pageState.runningText);
  const matchIndex = normalizedFull.indexOf(targetNormalized);
  if (matchIndex === -1) return false;

  const matchEnd = matchIndex + targetNormalized.length;
  pageState.spans.forEach(({ span, start }) => {
    const end = start + span.textContent.length;
    if (end > matchIndex && start < matchEnd) {
      span.classList.add(className);
    }
  });
  return true;
}

function ThumbnailImage({ pdfDoc, pageNum, isActive, onClick }) {
  const canvasRef = useRef(null);
  const wrapperRef = useRef(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    if (!wrapperRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !rendered && pdfDoc) {
          setRendered(true); // claim it immediately, render is async below
          pdfDoc.getPage(pageNum).then((page) => {
            const viewport = page.getViewport({ scale: THUMB_SCALE });
            const canvas = canvasRef.current;
            if (!canvas) return;
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const ctx = canvas.getContext("2d");
            page.render({ canvasContext: ctx, viewport }).promise.catch(() => {});
          });
        }
      },
      { rootMargin: "200px 0px" }
    );
    observer.observe(wrapperRef.current);
    return () => observer.disconnect();
  }, [pdfDoc, pageNum, rendered]);

  return (
    <button
      ref={wrapperRef}
      onClick={onClick}
      className={`block w-full border rounded overflow-hidden text-[10px] text-slate-300 pb-1 ${
        isActive ? "border-blue-500" : "border-slate-700"
      }`}
    >
      <div className="bg-white/5 aspect-[3/4] flex items-center justify-center text-slate-600 relative">
        <canvas ref={canvasRef} className="w-full h-full object-contain" />
        {!rendered && <span className="absolute">{pageNum}</span>}
      </div>
      <div className="mt-0.5">{pageNum}</div>
    </button>
  );
}

export default function PdfViewer({ document: doc, jumpToPage, highlightSnippet, onAskAboutSelection }) {
  const [pdfDoc, setPdfDoc] = useState(null);
  const [error, setError] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [pageSizes, setPageSizes] = useState([]); // [{width, height}] at RENDER_SCALE
  const [currentPage, setCurrentPage] = useState(1);
  const [sidebarTab, setSidebarTab] = useState(null); // null | 'thumbnails' | 'outline' | 'notes'
  const [outline, setOutline] = useState(null);
  const [annotations, setAnnotations] = useState([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMatches, setSearchMatches] = useState([]); // [{page}]
  const [searchIndex, setSearchIndex] = useState(0);
  const [selectionPopover, setSelectionPopover] = useState(null); // {x, y, text, page}
  const [notePrompt, setNotePrompt] = useState(null); // {text, page, xPercent, yPercent}

  const containerRef = useRef(null);
  const pageWrapperRefs = useRef(new Map());
  const pageState = useRef(new Map()); // pageNum -> {canvas rendered, spans, runningText}
  const pageTextCache = useRef(new Map()); // pageNum -> full text (for search, cheap to fetch)
  const searchInputRef = useRef(null);

  // --- Load document -------------------------------------------------
  useEffect(() => {
    if (!doc) {
      setPdfDoc(null);
      return;
    }
    let cancelled = false;
    setError(null);
    setPdfDoc(null);
    setOutline(null);
    pageState.current.clear();
    pageTextCache.current.clear();
    setSearchMatches([]);
    setSearchQuery("");

    api
      .get(`/documents/${doc.id}/file`, { responseType: "arraybuffer" })
      .then(async (response) => {
        if (cancelled) return;
        const loadingTask = pdfjsLib.getDocument({ data: response.data });
        const loaded = await loadingTask.promise;
        if (cancelled) return;

        const sizes = [];
        for (let i = 1; i <= loaded.numPages; i++) {
          const page = await loaded.getPage(i);
          const vp = page.getViewport({ scale: RENDER_SCALE });
          sizes.push({ width: vp.width, height: vp.height });
        }
        if (cancelled) return;

        setPdfDoc(loaded);
        setNumPages(loaded.numPages);
        setPageSizes(sizes);
        setCurrentPage(1);

        loaded.getOutline().then((o) => !cancelled && setOutline(o || []));
      })
      .catch((err) => {
        console.error(err);
        if (!cancelled) setError("Could not load this PDF.");
      });

    return () => {
      cancelled = true;
    };
  }, [doc]);

  useEffect(() => {
    if (!doc) return;
    listAnnotations(doc.id).then(setAnnotations).catch(() => setAnnotations([]));
  }, [doc]);

  // --- Render a single page (canvas + text layer) --------------------
  const renderPage = useCallback(
    async (pageNum) => {
      if (!pdfDoc || pageState.current.get(pageNum)?.rendered) return;
      const wrapper = pageWrapperRefs.current.get(pageNum);
      if (!wrapper) return;

      const canvas = wrapper.querySelector("canvas");
      const textLayerDiv = wrapper.querySelector(".pdf-text-layer");
      if (!canvas || !textLayerDiv) return;

      const page = await pdfDoc.getPage(pageNum);
      const viewport = page.getViewport({ scale: RENDER_SCALE });

      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const ctx = canvas.getContext("2d");

      try {
        await page.render({ canvasContext: ctx, viewport }).promise;
      } catch (err) {
        if (err?.name !== "RenderingCancelledException") console.error(err);
        return;
      }

      const textContent = await page.getTextContent();
      textLayerDiv.innerHTML = "";
      const spans = [];
      let runningText = "";

      textContent.items.forEach((item) => {
        const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
        const fontHeight = Math.hypot(tx[2], tx[3]);
        const span = window.document.createElement("span");
        span.textContent = item.str;
        span.style.position = "absolute";
        span.style.left = `${tx[4]}px`;
        span.style.top = `${tx[5] - fontHeight}px`;
        span.style.fontSize = `${fontHeight}px`;
        span.style.fontFamily = "sans-serif";
        span.style.color = "transparent";
        span.style.whiteSpace = "pre";
        span.style.lineHeight = "1";
        textLayerDiv.appendChild(span);
        spans.push({ span, start: runningText.length });
        runningText += item.str + " ";
      });

      pageTextCache.current.set(pageNum, runningText);
      pageState.current.set(pageNum, { rendered: true, spans, runningText });

      if (highlightSnippet && jumpToPage === pageNum) {
        highlightSpans(pageState.current.get(pageNum), normalize(highlightSnippet).slice(0, 80), "citation-highlight");
      }
    },
    [pdfDoc, highlightSnippet, jumpToPage]
  );

  // --- Lazy render on scroll via IntersectionObserver -----------------
  useEffect(() => {
    if (!pdfDoc || numPages === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const pageNum = Number(entry.target.dataset.page);
            renderPage(pageNum);
            setCurrentPage((prev) => (entry.intersectionRatio > 0.5 ? pageNum : prev));
          }
        });
      },
      { root: containerRef.current, rootMargin: "600px 0px", threshold: [0, 0.5] }
    );

    pageWrapperRefs.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [pdfDoc, numPages, renderPage]);

  // --- Jump to a cited page + highlight --------------------------------
  useEffect(() => {
    if (!jumpToPage || !pdfDoc) return;
    const wrapper = pageWrapperRefs.current.get(jumpToPage);
    if (!wrapper) return;
    wrapper.scrollIntoView({ behavior: "smooth", block: "start" });
    renderPage(jumpToPage).then(() => {
      if (highlightSnippet) {
        highlightSpans(pageState.current.get(jumpToPage), normalize(highlightSnippet).slice(0, 80), "citation-highlight");
      }
    });
  }, [jumpToPage, highlightSnippet, pdfDoc, renderPage]);

  // --- Search across the whole document --------------------------------
  const runSearch = async (query) => {
    if (!pdfDoc || !query.trim()) {
      setSearchMatches([]);
      return;
    }
    const target = normalize(query);
    const matches = [];

    for (let i = 1; i <= numPages; i++) {
      let text = pageTextCache.current.get(i);
      if (text === undefined) {
        const page = await pdfDoc.getPage(i);
        const content = await page.getTextContent();
        text = content.items.map((it) => it.str).join(" ") + " ";
        pageTextCache.current.set(i, text);
      }
      if (normalize(text).includes(target)) matches.push({ page: i });
    }

    setSearchMatches(matches);
    setSearchIndex(0);
    if (matches.length > 0) goToMatch(matches[0], query);
  };

  const goToMatch = async (match, query) => {
    const wrapper = pageWrapperRefs.current.get(match.page);
    if (!wrapper) return;
    wrapper.scrollIntoView({ behavior: "smooth", block: "start" });
    await renderPage(match.page);
    highlightSpans(pageState.current.get(match.page), normalize(query), "search-highlight");
  };

  const nextMatch = () => {
    if (searchMatches.length === 0) return;
    const next = (searchIndex + 1) % searchMatches.length;
    setSearchIndex(next);
    goToMatch(searchMatches[next], searchQuery);
  };
  const prevMatch = () => {
    if (searchMatches.length === 0) return;
    const prev = (searchIndex - 1 + searchMatches.length) % searchMatches.length;
    setSearchIndex(prev);
    goToMatch(searchMatches[prev], searchQuery);
  };

  // Ctrl+F / Cmd+F opens in-document search instead of the browser's own.
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "f" && doc) {
        e.preventDefault();
        setSearchOpen(true);
        setTimeout(() => searchInputRef.current?.focus(), 0);
      }
      if (e.key === "Escape") setSearchOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [doc]);

  // --- Text selection -> "Ask AI" / "Add note" -------------------------
  const handleMouseUp = () => {
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (!text || !containerRef.current) {
      setSelectionPopover(null);
      return;
    }
    const anchorNode = selection.anchorNode;
    if (!containerRef.current.contains(anchorNode)) return;

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();

    // Figure out which page this selection is in, and its normalized
    // position within that page (for the note marker).
    let page = currentPage;
    let xPercent = null;
    let yPercent = null;
    for (const [pageNum, el] of pageWrapperRefs.current.entries()) {
      const pr = el.getBoundingClientRect();
      if (rect.top >= pr.top && rect.top <= pr.bottom) {
        page = pageNum;
        xPercent = (rect.left - pr.left) / pr.width;
        yPercent = (rect.top - pr.top) / pr.height;
        break;
      }
    }

    setSelectionPopover({
      x: rect.left - containerRect.left + containerRef.current.scrollLeft,
      y: rect.top - containerRect.top + containerRef.current.scrollTop - 40,
      text,
      page,
      xPercent,
      yPercent,
    });
  };

  const askAboutSelection = () => {
    if (selectionPopover && onAskAboutSelection) {
      onAskAboutSelection(selectionPopover.text, selectionPopover.page);
    }
    setSelectionPopover(null);
    window.getSelection()?.removeAllRanges();
  };

  const startAddNote = () => {
    if (!selectionPopover) return;
    setNotePrompt({
      text: "",
      quote: selectionPopover.text,
      page: selectionPopover.page,
      xPercent: selectionPopover.xPercent,
      yPercent: selectionPopover.yPercent,
    });
    setSelectionPopover(null);
  };

  const submitNote = async () => {
    if (!notePrompt || !notePrompt.text.trim()) return;
    try {
      const created = await createAnnotation(doc.id, {
        page: notePrompt.page,
        note_text: notePrompt.text.trim(),
        quote_text: notePrompt.quote || null,
        x_percent: notePrompt.xPercent,
        y_percent: notePrompt.yPercent,
      });
      setAnnotations((prev) => [...prev, created]);
    } catch (err) {
      console.error(err);
      alert("Could not save the note.");
    } finally {
      setNotePrompt(null);
      window.getSelection()?.removeAllRanges();
    }
  };

  const removeNote = async (annotation) => {
    try {
      await deleteAnnotation(doc.id, annotation.id);
      setAnnotations((prev) => prev.filter((a) => a.id !== annotation.id));
    } catch (err) {
      console.error(err);
    }
  };

  const jumpToOutlineItem = async (item) => {
    if (!pdfDoc) return;
    try {
      const dest = typeof item.dest === "string" ? await pdfDoc.getDestination(item.dest) : item.dest;
      if (!dest) return;
      const pageIndex = await pdfDoc.getPageIndex(dest[0]);
      const wrapper = pageWrapperRefs.current.get(pageIndex + 1);
      wrapper?.scrollIntoView({ behavior: "smooth", block: "start" });
      renderPage(pageIndex + 1);
    } catch (err) {
      console.error("Could not resolve outline destination", err);
    }
  };

  const jumpToNote = (annotation) => {
    const wrapper = pageWrapperRefs.current.get(annotation.page);
    wrapper?.scrollIntoView({ behavior: "smooth", block: "start" });
    renderPage(annotation.page);
  };

  const notesByPage = useMemo(() => {
    const map = new Map();
    annotations.forEach((a) => {
      if (!map.has(a.page)) map.set(a.page, []);
      map.get(a.page).push(a);
    });
    return map;
  }, [annotations]);

  if (!doc) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400">
        Select a document to preview it here.
      </div>
    );
  }
  if (error) {
    return <div className="p-4 text-red-400">{error}</div>;
  }

  return (
    <div className="h-full flex flex-col bg-slate-950 rounded-lg border border-slate-700 overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-900 border-b border-slate-700 text-sm text-slate-300 shrink-0 gap-2 flex-wrap">
        <span className="truncate max-w-[40%]">{doc.filename}</span>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setSidebarTab(sidebarTab === "thumbnails" ? null : "thumbnails")}
            className={`px-2 py-1 rounded text-xs ${sidebarTab === "thumbnails" ? "bg-blue-600" : "bg-slate-700 hover:bg-slate-600"}`}
            title="Thumbnails"
          >
            🖼️
          </button>
          <button
            onClick={() => setSidebarTab(sidebarTab === "outline" ? null : "outline")}
            className={`px-2 py-1 rounded text-xs ${sidebarTab === "outline" ? "bg-blue-600" : "bg-slate-700 hover:bg-slate-600"}`}
            title="Bookmarks / Outline"
          >
            📑
          </button>
          <button
            onClick={() => setSidebarTab(sidebarTab === "notes" ? null : "notes")}
            className={`px-2 py-1 rounded text-xs ${sidebarTab === "notes" ? "bg-blue-600" : "bg-slate-700 hover:bg-slate-600"}`}
            title="Notes"
          >
            📝 {annotations.length > 0 && <span className="ml-0.5">{annotations.length}</span>}
          </button>
          <button
            onClick={() => {
              setSearchOpen((s) => !s);
              setTimeout(() => searchInputRef.current?.focus(), 0);
            }}
            className={`px-2 py-1 rounded text-xs ${searchOpen ? "bg-blue-600" : "bg-slate-700 hover:bg-slate-600"}`}
            title="Search (Ctrl+F)"
          >
            🔍
          </button>
          <span className="text-xs text-slate-400 ml-1">
            {currentPage} / {numPages || "?"}
          </span>
        </div>
      </div>

      {/* Search bar */}
      {searchOpen && (
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800 border-b border-slate-700 text-sm shrink-0">
          <input
            ref={searchInputRef}
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              runSearch(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") (e.shiftKey ? prevMatch() : nextMatch());
            }}
            placeholder="Search in document..."
            className="flex-1 bg-slate-700 text-white rounded px-2 py-1 outline-none text-sm"
            dir="auto"
          />
          <span className="text-xs text-slate-400 whitespace-nowrap">
            {searchMatches.length > 0 ? `${searchIndex + 1}/${searchMatches.length} pages` : "0 results"}
          </span>
          <button onClick={prevMatch} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs">↑</button>
          <button onClick={nextMatch} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs">↓</button>
          <button onClick={() => setSearchOpen(false)} className="px-2 py-1 text-slate-400 hover:text-white text-xs">✕</button>
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        {/* Sidebar */}
        {sidebarTab === "thumbnails" && (
          <div className="w-28 shrink-0 overflow-y-auto bg-slate-900 border-r border-slate-700 p-2 space-y-2">
            {Array.from({ length: numPages }, (_, i) => i + 1).map((n) => (
              <ThumbnailImage
                key={n}
                pdfDoc={pdfDoc}
                pageNum={n}
                isActive={currentPage === n}
                onClick={() => {
                  pageWrapperRefs.current.get(n)?.scrollIntoView({ behavior: "smooth", block: "start" });
                  renderPage(n);
                }}
              />
            ))}
          </div>
        )}

        {sidebarTab === "outline" && (
          <div className="w-56 shrink-0 overflow-y-auto bg-slate-900 border-r border-slate-700 p-3 text-sm">
            {outline === null && <p className="text-slate-500">Loading...</p>}
            {outline?.length === 0 && <p className="text-slate-500">No bookmarks in this PDF.</p>}
            <OutlineList items={outline} onSelect={jumpToOutlineItem} />
          </div>
        )}

        {sidebarTab === "notes" && (
          <div className="w-64 shrink-0 overflow-y-auto bg-slate-900 border-r border-slate-700 p-3 text-sm space-y-2">
            {annotations.length === 0 && <p className="text-slate-500">No notes yet — select text in the PDF to add one.</p>}
            {annotations.map((a) => (
              <div key={a.id} className="bg-slate-800 rounded p-2">
                <div className="flex justify-between items-start gap-2">
                  <button onClick={() => jumpToNote(a)} className="text-left flex-1">
                    <div className="text-xs text-blue-300 mb-1">Page {a.page}</div>
                    {a.quote_text && (
                      <div className="text-xs text-slate-400 italic mb-1 line-clamp-2">"{a.quote_text}"</div>
                    )}
                    <div className="text-slate-200 text-sm">{a.note_text}</div>
                  </button>
                  <button onClick={() => removeNote(a)} className="text-slate-500 hover:text-red-400 text-xs">✕</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Main scroll area */}
        <div
          ref={containerRef}
          onMouseUp={handleMouseUp}
          className="flex-1 overflow-auto relative"
        >
          {!pdfDoc && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-400 animate-pulse z-10">
              Loading PDF...
            </div>
          )}

          <div className="flex flex-col items-center gap-3 py-3">
            {pageSizes.map((size, idx) => {
              const pageNum = idx + 1;
              return (
                <div
                  key={pageNum}
                  data-page={pageNum}
                  ref={(el) => {
                    if (el) pageWrapperRefs.current.set(pageNum, el);
                    else pageWrapperRefs.current.delete(pageNum);
                  }}
                  className="relative bg-white/5"
                  style={{ width: size.width, height: size.height }}
                >
                  <canvas className="block" />
                  <div className="pdf-text-layer absolute inset-0 overflow-hidden pointer-events-auto" />

                  {(notesByPage.get(pageNum) || []).map((a) =>
                    a.x_percent != null ? (
                      <button
                        key={a.id}
                        onClick={() => jumpToNote(a)}
                        title={a.note_text}
                        className="absolute w-4 h-4 rounded-full bg-yellow-400 border border-yellow-600 text-[9px] flex items-center justify-center"
                        style={{ left: `${a.x_percent * 100}%`, top: `${a.y_percent * 100}%` }}
                      >
                        📝
                      </button>
                    ) : null
                  )}
                </div>
              );
            })}
          </div>

          {/* Text-selection popover */}
          {selectionPopover && (
            <div
              className="absolute z-20 flex gap-1 bg-slate-800 border border-slate-600 rounded-lg shadow-lg p-1"
              style={{ left: selectionPopover.x, top: Math.max(0, selectionPopover.y) }}
            >
              <button
                onClick={askAboutSelection}
                className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs text-white whitespace-nowrap"
              >
                💬 Ask AI about this
              </button>
              <button
                onClick={startAddNote}
                className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs text-white whitespace-nowrap"
              >
                📝 Add note
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Add-note inline prompt */}
      {notePrompt && (
        <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-30 p-4">
          <div className="bg-slate-800 rounded-lg p-4 w-full max-w-sm">
            <div className="text-xs text-slate-400 mb-1">Page {notePrompt.page}</div>
            {notePrompt.quote && (
              <div className="text-xs text-slate-400 italic mb-2 line-clamp-3">"{notePrompt.quote}"</div>
            )}
            <textarea
              autoFocus
              value={notePrompt.text}
              onChange={(e) => setNotePrompt({ ...notePrompt, text: e.target.value })}
              placeholder="Your note..."
              dir="auto"
              className="w-full p-2 rounded bg-slate-700 text-white text-sm outline-none"
              rows={3}
            />
            <div className="flex justify-end gap-2 mt-3">
              <button onClick={() => setNotePrompt(null)} className="text-slate-400 hover:text-white text-sm px-3 py-1.5">
                Cancel
              </button>
              <button onClick={submitNote} className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1.5 rounded">
                Save Note
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .citation-highlight { background-color: rgba(250, 204, 21, 0.45); border-radius: 2px; }
        .search-highlight { background-color: rgba(251, 146, 60, 0.55); border-radius: 2px; }
      `}</style>
    </div>
  );
}

function OutlineList({ items, onSelect, depth = 0 }) {
  if (!items || items.length === 0) return null;
  return (
    <ul className={depth > 0 ? "ml-3 border-l border-slate-700 pl-2" : ""}>
      {items.map((item, i) => (
        <li key={i} className="py-0.5">
          <button
            onClick={() => onSelect(item)}
            className="text-left text-slate-300 hover:text-white text-xs"
            dir="auto"
          >
            {item.title}
          </button>
          {item.items?.length > 0 && <OutlineList items={item.items} onSelect={onSelect} depth={depth + 1} />}
        </li>
      ))}
    </ul>
  );
}
