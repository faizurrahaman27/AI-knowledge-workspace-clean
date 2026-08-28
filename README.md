# Production RAG Chatbot — Regulated-Vertical Capstone

A Retrieval-Augmented Generation chatbot: upload a PDF, ask questions, get
answers grounded in that document with page-level citations. Built to align
with the "Production RAG Chatbot for a Regulated Vertical" capstone spec
(auth + RBAC, hybrid retrieval + reranking, citations, guardrails,
evaluation, observability, containerized deployment).

## Before you do anything else

An earlier version of this repo had a **live-looking OpenAI API key** committed
in `backend/.env`, and it is still present in old git commits even though the
current `.env` is now gitignored. If this repo was ever pushed publicly:

1. **Revoke that key now** at platform.openai.com -> API keys.
2. Rewrite git history to remove it (`git filter-repo --path backend/.env
   --invert-paths`, or start a fresh repo) -- deleting the file today does not
   remove it from history.
3. Copy `backend/.env.example` to `backend/.env` and fill in your **own**
   secrets. Never commit `.env`.

## Architecture

```
PDF Upload -> Extract Text -> Chunk -> Embed -> ChromaDB
                                              |
User Question -> Embed ----------------------->|
                                              v
                          Hybrid Retrieval (dense + BM25, RRF-fused)
                                              |
                                              v
                          Cross-Encoder Reranker (top 5)
                                              |
                                              v
                    Guardrails (prompt-injection block, PII flag)
                                              |
                                              v
                       Llama 3.2 (via Ollama) -- streamed generation
                                              |
                                              v
                    Answer (SSE) + Citations (page/chunk) + Audit log
```

## What changed in this pass

### Security fixes
- Removed the leaked OpenAI key from `.env`; added `.env.example`.
- `db/database.py` had a **second, hardcoded** SQLite connection string that
  silently ignored `DATABASE_URL` from settings -- fixed to use one source of
  truth, so switching to Postgres via `.env` actually works.
- Removed `print()` statements in `auth_service.py` / `dependencies/auth.py`
  that logged **plaintext passwords, password hashes, and full user tables**
  to server stdout on every login attempt. Replaced with structured,
  secret-free logging.
- CORS was `allow_origins=["*"]` -- now reads an explicit allow-list from
  `CORS_ORIGINS` in `.env`.
- PDF upload validated only the `.pdf` **extension**; a renamed `.exe` would
  pass. Now checks the actual file's magic bytes (`%PDF-`) and enforces
  `MAX_UPLOAD_MB`.
- `DocumentResponse` returned the server's local filesystem `file_path` to
  the client for no functional reason -- removed.
- `backend/requirements.txt` was missing most packages the code actually
  imports (chromadb, sentence-transformers, PyMuPDF, ollama, python-jose,
  passlib, rank-bm25, prometheus-client, python-multipart...) -- `pip install
  -r requirements.txt` would not have produced a runnable app. Rewritten with
  every real dependency, pinned.
- `frontend/package.json` was missing `react-markdown` and `remark-gfm`,
  which `ChatPanel.jsx` already imports -- `npm install` followed by
  `npm run dev` would have crashed. Added and verified `npm run build`
  succeeds.
- Dropped `passlib` entirely and call `bcrypt` directly for password hashing.
  `passlib==1.7.4` is unmaintained and crashes against `bcrypt>=4.1`
  (`AttributeError: module 'bcrypt' has no attribute '__about__'`) because it
  probes an internal attribute bcrypt removed. Pinning `bcrypt==4.0.1` was a
  workaround but re-breaks the moment anything upgrades bcrypt; calling
  `bcrypt.hashpw`/`bcrypt.checkpw` directly (see `core/security.py`) removes
  the fragile dependency instead of chasing pins. Also fixed the related
  bcrypt 72-byte password limit to truncate safely instead of raising.
- There were **two competing route handlers** for `GET /chat/{document_id}`
  (one in `api/chat.py`, one in `api/history.py`), both registered -- the
  second was silently dead code. Consolidated into one, typed endpoint.

### New capstone-required features
- **RBAC**: `User.role` (`admin` / `employee` / `customer`), a
  `require_roles()` dependency, admin-only user-provisioning/listing routes,
  and a bootstrap mechanism for the first admin account (`BOOTSTRAP_ADMIN_EMAIL`
  / `BOOTSTRAP_ADMIN_PASSWORD` in `.env`).
- **Refresh tokens**: short-lived access token + long-lived refresh token,
  `POST /auth/refresh`.
- **Rate limiting**: in-memory sliding-window limiter on
  `/auth/*` and `/chat/*` (swap for Redis if you scale to multiple workers --
  see `core/rate_limit.py` docstring).
- **Hybrid retrieval**: dense vector search (Chroma) fused with BM25 lexical
  search via Reciprocal Rank Fusion, *then* cross-encoder reranked. See
  `utils/vector_store.py::hybrid_search`.
- **Citations returned to the client**, not just printed server-side: the
  chat stream ends with a `\n\n[[CITATIONS]]<json>` payload the frontend
  parses and renders as a "Sources: file - page" line. Citations are also
  persisted per chat turn for audit purposes (`Chat.citations`).
- **Guardrails** (`utils/guardrails.py`): heuristic prompt-injection/jailbreak
  detection (blocks the turn) and PII pattern detection (flags/redacts for
  logging), with unit tests.
- **Evaluation harness** (`evaluation/evaluate_retrieval.py`): dependency-free
  Hit Rate@k / MRR / latency scoring against a labeled test set, with notes
  on upgrading to Ragas/DeepEval if you have an LLM-judge API key.
- **Observability**: `/metrics` (Prometheus text format) via
  `prometheus-client`, request-latency middleware, chat-specific counters.
- **Deployment**: `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`,
  root `docker-compose.yml`, `docker/nginx.conf` (proxies `/api/` to the
  backend with buffering off so SSE streaming works), and a CI workflow
  (`.github/workflows/ci.yml`) that runs the backend test suite and frontend
  build on every push.
- **Tests**: `backend/tests/` (pytest) covering auth, RBAC, refresh tokens,
  rate limiting, guardrails, and chunking -- 16 tests, all passing, run
  offline via stubbed ML dependencies (see `tests/stubs/`).

## Running locally

```bash
# Backend
cd backend
cp .env.example .env        # fill in SECRET_KEY, REFRESH_SECRET_KEY (openssl rand -hex 32)
pip install -r requirements.txt
ollama pull llama3.2         # requires Ollama installed separately
uvicorn src.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Running tests

```bash
cd backend
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-dotenv \
  email-validator "python-jose[cryptography]" "bcrypt==4.2.1" \
  rank-bm25 prometheus-client python-multipart pytest httpx
python -m pytest tests/ -v
```

### Running with Docker

```bash
cp backend/.env.example backend/.env   # fill in secrets first
docker compose up --build
# frontend: http://localhost
# backend:  http://localhost:8000  (proxied through nginx at /api/ from the frontend)
```

## Honest scope notes (what's NOT done, and why)

A few items from the original spec need infrastructure or paid services this
sandbox can't provide or verify, so they're intentionally left as documented
next steps rather than faked:

- **Kubernetes**: `docker-compose.yml` covers single-host production; a
  Helm chart / k8s manifests are a reasonable next step once you have a
  cluster to test against.
- **Grafana dashboards**: `/metrics` is wired and Prometheus-scrapeable;
  building actual dashboard JSON without a running Prometheus+Grafana stack
  to validate against would just be guessing.
- **Cohere/OpenAI reranker or embeddings**: the pipeline uses local,
  open-source models (SentenceTransformer + cross-encoder) so it runs with
  zero API cost; swapping in a hosted reranker is a config change in
  `utils/reranker.py` if you want the accuracy/latency trade-off.
- **DOCX/TXT/HTML ingestion**: only PDF is implemented; `utils/pdf.py` is the
  place to add sibling loaders following the same `extract_pages_from_pdf`
  contract.

## Roadmap (unchanged priority order from the original plan)

1. Streaming (done), Markdown rendering (done), Citations (done) -- remaining:
   syntax-highlighted code blocks, regenerate-response button.
2. Click-to-highlight from a citation into the original PDF viewer.
3. Filename search, renameable/auto-titled conversations, suggested
   follow-up questions, chat export (PDF/Markdown/text).
4. Kubernetes, Grafana dashboards, additional file-type ingestion.

## Phase 9: Knowledge Workspace features (this update)

### Built and verified
- **Live backend pipeline visualization**: `/chat/` now streams NDJSON
  (one JSON object per line) instead of raw text. Event types: `status`
  (guardrail/embedding/retrieval/rerank/generation/translation stages, each
  with a `done` flag), `token` (answer text), `citations`, `translation`,
  `done`. The frontend renders each `status` event as a live checklist
  above the answer as it streams in.
- **PDF viewer beside chat**: `GET /documents/{id}/file` streams the
  original PDF back to its owner (auth-checked); the frontend fetches it as
  a blob and renders it in an `<iframe>`. Clicking a citation jumps the
  viewer to that page via the browser's native `#page=N` PDF fragment —
  no extra pdf.js dependency needed for this.
- **Dual-language answers**: document language is detected at ingestion
  (`langdetect`, offline, no API). The primary answer is generated in the
  document's language; if that's not English, a second, non-streamed
  translation call produces an English version, sent as a `translation`
  event. The frontend shows a "Show English translation" toggle per answer.
- **Voice output**: answers and scan summaries get a 🔊 Listen button using
  the browser's built-in Web Speech API (`speechSynthesis`) — free, offline,
  and the Scan panel lets you pick from whatever voices your OS/browser
  exposes (this is how you get "male/female/accent" options without any
  paid TTS API).
- **Scan & OCR** (`POST /scan/analyze`): upload a photo (receipt, note,
  whiteboard, book page, ID) and get OCR'd text (Tesseract, offline) plus a
  short spoken-style "what's useful here" summary.
- **Study Mode** (`POST /study/`): Summarize / Important Questions / Quiz /
  Flashcards / Revision Notes / Cheat Sheet, generated from a representative
  sample of the whole document (not just top-k search results).
- **"Explain like..."**: a level selector (Beginner/Student/Engineer/
  Professor/Explain-like-I'm-10/Interview) that changes the answer's tone
  via the prompt, no extra infra needed.

### Explicitly NOT built (and why)
These need real infrastructure or hardware this sandbox can't provide or
verify, so they're documented here rather than faked:
- **Camera scanning with auto-crop/deskew/multi-page merge**: needs a real
  device camera and image-processing pipeline (OpenCV deskew/perspective
  correction) that has to be tuned against real photos to be worth shipping.
  `ScanPanel` currently accepts a single uploaded photo; wiring
  `<input capture="environment">` for direct camera capture is the easy
  first step if you want to extend this yourself.
- **Speech-to-text question input**: the Web Speech API's `SpeechRecognition`
  (not `SpeechSynthesis`, which we do use) can do this client-side in Chrome
  with no backend change — reasonable next step, just not done here.
- **True visual/diagram understanding**: needs a multimodal vision LLM
  (Llama 3.2 text-only here does not "see" images) — OCR text-extraction is
  what's implemented, not diagram/chart comprehension.
- **Multi-document comparison, mind maps, multi-agent orchestration**:
  each is a real feature design exercise on its own (comparison needs
  retrieval across two documents' collections and a diff-style prompt; mind
  maps need a structured-output format the frontend can render as a tree;
  multi-agent orchestration needs a defined task-decomposition strategy) —
  scoping and building any one properly is more than a drop-in addition.
- **Confidence scoring**: would need either logprob access (Ollama's
  Python client doesn't expose token-level probabilities the way OpenAI's
  does) or a second LLM-as-judge call — worth doing deliberately, not
  bolted on.

If you want any of the "not built" items next, the cleanest path is one at
a time, the same way this batch was done: real code, real tests, honest
about what doesn't work yet.

## Phase 9 — remaining items, now built

Everything from the previous "not built" list has a real implementation now,
each honestly scoped:

- **Speech-to-text question input**: 🎤 button in Chat uses the browser's
  `SpeechRecognition` API (Chrome/Edge) to fill the question box by voice.
- **Camera document scanning**: new "Camera Scan" tab opens the device
  camera (`getUserMedia`), captures one photo per page, and merges them into
  a single PDF (`img2pdf`) that runs through the exact same ingestion
  pipeline as a normal upload — full RAG chat, citations, page-jump, all of
  it. **Honest caveat, stated in the UI too**: no auto-crop/deskew/perspective
  correction yet — frame pages squarely for best OCR results. That's a
  well-scoped next step (OpenCV contour detection + perspective transform)
  if you want it.
- **Visual/diagram understanding** (`POST /scan/understand-visual`, via
  `utils/vision.py`): with the default `LLM_PROVIDER=groq`, this calls
  Groq's vision-preview model over HTTP — a real, testable API call, and
  it's covered by the test suite. If you switch to `LLM_PROVIDER=ollama`,
  it instead requires `ollama pull llama3.2-vision` (multi-GB) and that
  code path is **not** verified at runtime in this sandbox (no network
  access to pull model weights) — test it yourself before relying on it.
  Not yet wired to a frontend button.
- **Multi-document comparison** (`POST /compare/`, "Compare" tab): retrieves
  from two documents independently, then asks the model to compare them
  against your question, streamed the same way chat is.
- **Mind maps** (`POST /mindmap/`, "Mind Map" tab): asks the model for a
  strict JSON topic tree, parsed defensively (models sometimes wrap JSON in
  prose despite instructions), rendered as a collapsible tree.
- **Confidence scoring**: derived from the cross-encoder reranker's top
  score, squashed to a High/Medium/Low badge on each answer. This is a
  genuine, explained proxy signal ("how well did the best passage match the
  question"), not a fabricated probability — see `utils/confidence.py`'s
  docstring for exactly what it does and doesn't mean.
- **Lightweight multi-agent-style orchestration** (`POST /agent/`): a single
  intent-classification call routes a free-text request to summary/quiz
  generation directly, or tells the frontend which specialist endpoint
  (chat/compare/mindmap) to call. This is deliberately named an
  "orchestrator," not "multiple autonomous agents" — that's a materially
  bigger system (independent planning loops, tool-call negotiation between
  agents) that this single-router pattern doesn't claim to be.

### Still genuinely open, if you want to keep going
- Auto-crop/deskew for camera-scanned pages (OpenCV).
- Verifying `llama3.2-vision` end-to-end (needs the model pulled locally)
  and adding a frontend button for `/scan/understand-visual`.

## LLM provider: Groq (default, fast) vs Ollama (local, private)

Ollama on CPU-only hardware can take minutes per answer for a 70B-class
model, or be noticeably slow even at 3B without a GPU — that's real,
not a bug. **Groq is now the default** because it runs the *same kind* of
open-weight models (Llama 3.3, etc.) on purpose-built inference hardware:
typical answers come back in 1-3 seconds instead of tens of minutes.

**Setup (one-time, free, no credit card):**
1. Go to https://console.groq.com/keys, sign up, create a key.
2. In `backend/.env`: `GROQ_API_KEY=gsk_...`
3. That's it — `LLM_PROVIDER=groq` is already the default in `.env.example`.

**Honest tradeoff:** with Groq, the document context and your questions are
sent to Groq's API for the generation step (embeddings, search, reranking,
and OCR all stay 100% local either way). If that's not acceptable for your
data, set `LLM_PROVIDER=ollama` in `.env` and go back to fully local — it'll
just be slower without a GPU. Both paths run through the exact same code
(`utils/llm.py`'s provider dispatch), switching is a one-line `.env` change,
not a code change, and the whole test suite (`tests/test_llm_provider.py`)
exercises both.

**Which Groq model:** `.env.example` defaults to `llama-3.3-70b-versatile`
(best quality, still fast). For even lower latency on simple questions,
`llama-3.1-8b-instant` is worth trying — change `GROQ_MODEL` in `.env`.

## Free deployment (Hugging Face Spaces)

With Groq handling generation, the backend no longer needs a beefy VPS —
embeddings/reranking/OCR are lightweight CPU work. That makes a genuinely
free host viable:

1. Create a new Space at https://huggingface.co/new-space, SDK = **Docker**.
2. Push this repo's contents to the Space's git remote, but:
   - Replace the Space's auto-created `README.md` with
     `HUGGINGFACE_SPACE_README.md` from this repo (rename it to `README.md`
     at the Space's root — HF reads the YAML frontmatter in it to configure
     the Space).
   - Make sure `docker/Dockerfile.single` is present; in the Space's
     settings, or via a root-level `Dockerfile` that just does
     `FROM` + copies it, point the build at `docker/Dockerfile.single`
     (simplest: copy its contents to a `Dockerfile` at the repo root).
3. In the Space's **Settings → Repository secrets**, add `GROQ_API_KEY`,
   `SECRET_KEY`, `REFRESH_SECRET_KEY` (generate with `openssl rand -hex 32`).
   Do **not** commit real secrets into `.env` in a public Space.
4. Push. The Space builds and gives you a public URL automatically —
   share that URL, open it on a laptop or phone, both work (the frontend
   is responsive: drawer sidebar and stacked layout on small screens).

**Be honest with yourself about free-tier storage:** Spaces' free CPU tier
has ephemeral disk by default — uploaded PDFs, the vector index, and the
SQLite DB can be wiped on a rebuild/restart unless you enable persistent
storage (a paid Spaces upgrade) or point `DATABASE_URL` at a free external
Postgres (e.g. Neon/Supabase free tier) and swap Chroma's `PersistentClient`
path to a mounted persistent volume. Fine for a public demo; not fine as
someone's only copy of their documents.

**Prefer a VPS instead?** The original `docker-compose.yml` +
`Dockerfile.backend`/`Dockerfile.frontend` two-container setup (nginx +
backend) still works exactly as documented above, and now needs far less
RAM than before since Ollama is no longer required on the box itself.

## Status check against the "V2.0 Product Polish" roadmap

Went through this pass item by item. Marked exactly as it stands — including
things that looked done but weren't (a Logout button with no click handler,
a completely empty/unused `ProtectedRoute.jsx`, a login form that
`console.log`-ed the plaintext password, a broken refresh-token flow the
frontend never actually called). All of those are fixed now, not just noted.

### Priority 1 — User Experience
- ✅ Google Sign-In (needs your own free `GOOGLE_CLIENT_ID` — see `.env.example`; button hides itself if unset)
- ✅ Logout (was previously a dead button, not even mounted anywhere — now works)
- ✅ Forgot Password / Reset Password (dev-mode: link is logged to the server console unless you configure SMTP)
- ✅ User Profile page (account info, sign-in method)
- ✅ Settings (change password, log out on all devices)
- ✅ Theme (Dark/Light) — global toggle, persisted per-account
- ❌ Email Verification — not built. Needs the same SMTP setup as password reset; a bounded follow-up, not done here.

### Priority 2 — PDF Experience
- ✅ Page-jump on citation click (already had this)
- ⚠️ Paragraph-level highlight overlay — **not built**. The current viewer is a plain `<iframe>` using the browser's native PDF renderer, which can jump to a page via URL fragment but can't draw a highlight on top of it. Doing this properly means replacing the iframe with a `pdf.js`-rendered canvas + text layer — a real rewrite of `PdfViewer.jsx`, not a small addition, and risky to do without visual verification. Left honestly undone rather than faked.

### Priority 3 — Multilingual
- ✅ Language detection + dual-language answers (already had this)
- ❌ Per-language embedding models, mixed-language-PDF handling, OCR-language fallback — not built; current approach is language-agnostic by default (SentenceTransformer's multilingual coverage is decent but not tuned per-language). Real improvement, not done here.

### Priority 4 — Voice AI
- ✅ Speech-to-text question input (already had this)
- ✅ Text-to-speech answers, selectable voices (already had this)
This priority was already essentially complete before this pass.

### Priority 5 — Study Features
- ✅ Static Study Mode (summary/quiz/flashcards/etc, already had this)
- ❌ Adaptive flashcards, spaced repetition, timed tests, progress tracking/analytics — not built. These need new persisted models (attempts, scores, review scheduling) and are a real feature project on their own, not a bolt-on.

### Priority 6 — AI Agent
- ✅ Single-step intent router (already had this, `/agent`)
- ❌ Chained multi-step workflows (summarize → mindmap → flashcards → quiz → export) — not built this pass.

### Priority 7 — Security
- ✅ Google OAuth (backend + frontend wired, needs your credentials)
- ✅ Refresh-token rotation/revocation (token_version-based — password change and "logout everywhere" now actually invalidate old tokens, which they didn't before)
- ✅ Account lockout after repeated failed logins
- ✅ File validation (already had this)
- ✅ Secrets management via `.env` (already had this)
- ✅ RBAC (already had this)
- ❌ Audit logs (structured, queryable) — only informal logger.info() calls exist, not a real audit trail
- ❌ Two-Factor Authentication — not built
- HTTPS — deployment-environment concern, not application code; covered in the deployment section above (put this behind any reverse proxy with a free Let's Encrypt cert, or Hugging Face Spaces' automatic HTTPS)

### Also fixed this pass (not on the list, but real bugs)
- `ForgotPassword`/`Register` pages had bugs: a `console.log` leaking the raw password, `Register.jsx`'s form state initializing the wrong field name (`username` instead of `full_name`, an uncontrolled-input bug), routes with zero auth protection despite a `ProtectedRoute.jsx` file existing (it was empty and unused).
- Backend: SQLite strips timezone info from stored datetimes, which crashed the new account-lockout and password-reset expiry checks the moment they were exercised by a real test — fixed by normalizing to naive UTC consistently.

### Mobile app
Went with a **PWA** (installable web app), not a native store app — genuinely free, no Apple/Google developer account needed, installs on both iOS and Android home screens, works offline for the app shell. Real tradeoffs, stated plainly: it's not in the App Store/Play Store (nothing to "download" from a store search), and a true native wrapper (Capacitor) is possible later but costs real money (Apple Developer Program is $99/year, needs a Mac to build for iOS) and wasn't something to spend your money on without you asking for it specifically.

### V3.0 — status update: this is now built and tested

Everything below was built and verified with real tests since the section above
was written (that section is left in place, unedited, so you can see exactly
what changed and when):

- ✅ **Multi-document workspaces** — group documents together (`Workspace`
  model), chat searches across every document in the workspace at once
  (`hybrid_search_multi`, RRF-merged), scoped access control (personal vs
  team-owned). Tested: creation, document assignment/removal, cross-document
  retrieval, access denial for non-members.
- ✅ **Team accounts** — `Team`/`TeamMembership`/`TeamInvite` models, owner/
  admin/member roles, email invites (dev-mode: logged to console without
  SMTP configured, same as password reset), accept-invite flow that rejects
  a token used by the wrong email. Tested: creation, invite→accept, role
  permission checks (non-admin can't invite), wrong-email rejection.
- ✅ **Live collaboration** — a real-time layer, honestly scoped: every
  member connected to a workspace gets pushed the completed answer the
  instant *anyone* in that workspace asks a question, plus a live "N
  online" presence count (`/ws/workspace/{id}`, WebSocket). **What this is
  not**: live cursors, character-by-character collaborative editing, or
  conflict resolution (CRDT/OT) — there's nothing to resolve, since only
  one person's message is "in flight" at a time and everyone else just
  receives the finished result. Also single-process in-memory (documented
  in `core/ws_manager.py`): fine for the one-container deployment this
  project ships with, would need Redis pub/sub to fan out across multiple
  backend instances. Tested: auth rejection (missing/invalid token),
  access-control rejection (workspace you're not a member of), presence
  broadcast, and the actual chat-message broadcast reaching a second
  connected client while excluding the sender's own echo.
- ✅ **Chained AI agent workflow** — `POST /agent/study-pack`: Summary →
  Important Questions → Flashcards → Quiz → Mind Map, five sequential LLM
  calls, one document. **What this is not**: an autonomous planner that
  decides its own steps — it's a fixed pipeline, which is an honest
  description of what's implemented (see `api/agent.py`'s own docstring).
  Also downloadable as a real PDF (`reportlab`, not a placeholder — the
  test checks for actual `%PDF` magic bytes in the response).
- ✅ **Basic progress tracking / "personalized learning"** — a
  `QuizAttempt` history log (what you studied, when) plus a heuristic
  suggestion list (documents you uploaded but haven't generated study
  material for yet). **What this is not**: spaced repetition, adaptive
  difficulty, or an ML recommendation model — see `api/activity.py`'s own
  docstring, which says exactly this.

Also fixed while wiring the frontend for all of the above: nginx wasn't
configured to proxy WebSocket upgrade headers, which would have silently
broken live collaboration the moment this ran behind the two-container
deployment (only worked in raw local dev) — fixed in `docker/nginx.conf`.

### Still not built, honestly
- Paragraph-level PDF highlighting (Priority 2 above) — same reasoning as before, unchanged.
- Email verification, 2FA, structured audit logs (Priority 1/7 above) — unchanged.
- Per-language embedding tuning, adaptive/spaced-repetition study (Priority 3/5 above) — unchanged.
- Cross-process live collaboration at multi-instance scale (needs Redis pub/sub — noted above, not silently ignored).
- A true multimodal "AI agent" that plans its own steps rather than following a fixed pipeline — same distinction Priority 6 always drew; still accurate.

## The five previously-open items — status now

Went through each one. Most had already been substantially built in an
earlier pass but weren't wired to an API route or tested — I audited each,
found the real gaps, fixed them, and wrote tests that actually exercise
the behavior (not just check it compiles).

- ✅ **Email verification** — `resend_verification_email`/`verify_email`
  (dev-mode console log without SMTP, same pattern as password reset).
  Already built and tested (`test_email_and_2fa.py`).
- ✅ **2FA (TOTP)** — setup/confirm/disable + backup codes, login flow
  correctly interrupts for a 2FA code before issuing tokens. Already built
  and tested.
- ✅ **Spaced repetition** — SM-2 scheduling on flashcard reviews (easiness
  factor, interval, next-review-date), due-cards endpoint. Already built
  and tested (`test_spaced_repetition.py`, `test_flashcards.py`).
- ✅ **True autonomous agent planning** — this one had the hard part built
  (`utils/autonomous_agent.py`: a real Groq function-calling loop where the
  model picks which tool to call next, not a fixed sequence) but **no API
  route and zero tests** — the actual gap I closed this pass. Added
  `POST /agent/auto`, wrote 7 tests exercising it (no-tool-needed,
  single-tool, multi-tool, MAX_STEPS cutoff, ownership check, provider
  guard, malformed-tool-name recovery). **Found and fixed a real bug while
  testing it**: `rerank()` was changed elsewhere to return 3 values
  `(docs, metadatas, scores)`, but this file still unpacked 2 —
  `docs, metas = rerank(...)` — which would have crashed the
  `search_document` tool on every real call, silently caught by the
  loop's try/except and reported as "tool failed" rather than surfacing
  the actual bug. Confirmed no other caller had the same mistake.
- ✅ **Paragraph-level PDF highlighting** — the one genuinely new build
  this pass. Replaced the `<iframe>` viewer with real `pdf.js` canvas +
  text-layer rendering (`PdfViewer.jsx`), and citations now carry a text
  snippet (`Citation.snippet`, added to the backend response) that the
  viewer fuzzy-matches against the rendered page's extracted text and
  highlights. **Found and fixed a real bug while building this**: the
  component's `document` prop (the file metadata object) was shadowing
  the global `document.createElement` used to build the text layer —
  would have crashed immediately on first citation click. Fixed to use
  `window.document` explicitly.
  **Honest limitations, not hidden**: (1) this is frontend-only code — I
  cannot render a browser in this sandbox to visually confirm the
  highlight lands pixel-perfect, only that it builds and the matching
  logic is sound; test it yourself before trusting it fully. (2) PDF text
  extraction doesn't always align character-for-character with the
  original chunk text (ligatures, hyphenation, multi-column reordering),
  so some citations won't find a highlight match — the code detects this
  and logs it rather than highlighting the wrong text. (3) `pdfjs-dist`
  adds real weight: the worker bundle is ~2.2MB. Lazy-loading it via
  dynamic `import()` so it's not in the main bundle for users who never
  open the Chat tab would be a reasonable next optimization, not done here.

## Repositioning: "AI Knowledge Workspace," honestly assessed

Reasonable ask, and the underlying claim is now actually true, not just
marketing: this isn't "upload a PDF, ask ChatGPT-shaped questions" anymore
— multi-document workspaces, team-shared access, live collaboration,
chained and autonomous study workflows, spaced repetition, and citation
verification with page-level highlighting are all real, tested features
that a bare ChatGPT-with-a-PDF-upload doesn't have. That's the honest
version of the "why not just use ChatGPT" answer from the document above.

What's **not** built, stated the same way as everywhere else in this
README: live retrieval connectors (GitHub/Wikipedia/Arxiv/Confluence/
Slack), a real knowledge-graph engine (the Mind Map feature is a
per-document topic tree, not a persistent cross-document graph), true
multimodal ingestion (audio/video), and a Socratic adaptive-tutor dialogue
system. Each is a legitimate, separate multi-week product surface. If one
of those is the actual next priority, say which one and it'll get the same
treatment as everything above: real code, real tests, honest about limits.

## "Reading in any language" — what was actually missing and what's fixed

Good catch — three real gaps existed here, all silently limiting things to
English regardless of the document's actual language:

- **OCR was English-only.** `pytesseract.image_to_string(image)` was
  called with no `lang` parameter, so Tesseract defaulted to its `eng`
  model no matter what language was in the photo. Fixed: `Dockerfile.backend`
  and `Dockerfile.single` now install `tesseract-ocr-all` (every bundled
  language pack, ~600MB), and the Scan feature does a two-pass OCR when no
  language is specified — a broad multi-language pass to figure out what
  it's looking at, then a second pass targeted at the detected language for
  better accuracy (Tesseract is more accurate with one language than a
  dozen combined). You can also pick the language explicitly up front from
  the new dropdown in Scan & Listen, skipping straight to the targeted
  pass. Tested (`test_scan_languages.py`): the two-pass logic, the
  explicit-language skip, and the too-short-to-detect fallback.
- **Text-to-speech ignored the answer's actual language.** `speak()`
  created a `SpeechSynthesisUtterance` with no `.lang` set, so a Hindi or
  Telugu answer would get read in the browser's default (usually English)
  voice — badly mispronounced, not actually "read." Fixed: answers are now
  spoken with `utterance.lang` set from the document's detected language
  (BCP-47 tag, e.g. `hi-IN`), and a matching installed voice is picked
  automatically when the OS/browser has one. Same fix applied to Scan &
  Listen's summary readout, and there's now a separate "🔊 Listen in
  English" button for the translation specifically.
- **Voice input (speech-to-text) was hardcoded to `en-US`.** Asking a
  question by voice in Hindi about a Hindi document would fail or
  transcribe nonsense. Fixed: defaults to the selected document's detected
  language, with a manual override dropdown next to the mic button for
  when you want to ask in a different language than the document.

**Honest limits, not hidden:** whether a given language actually sounds
right depends on your OS/browser having a voice installed for it — this
can request the right language, it can't install a voice that isn't
there. Windows in particular ships far fewer non-English voices by default
than macOS or ChromeOS. Also, PDF *text* extraction (not OCR — actual
embedded PDF text) already handled any language correctly before this
change, since PyMuPDF extracts Unicode text directly; this fix was
specifically about OCR (photos/scans) and speech, which were the two
places English was silently assumed.

## "Same output in whatever language" — the real question, answered honestly

You asked specifically: upload an Arabic PDF, does it detect that and
answer in Arabic? The LLM-instruction part of this already worked (the
prompt already said "write your entire answer in Arabic" when the
document was Arabic) — but I found the retrieval underneath it was
quietly broken for Arabic, which means it could be generating a
fluent-sounding Arabic answer built on the wrong (or no) retrieved
passages. Grounded generation only means something if the grounding is
real. Three fixes, in order of severity:

1. **BM25 keyword search found ZERO tokens in Arabic text.** The
   tokenizer regex was `[a-z0-9]+` — literally only Latin letters and
   digits. I proved this directly: `_tokenize("مرحبا بكم...")` returned
   `[]`. Since hybrid retrieval fuses dense (vector) search with BM25
   (keyword) search, this meant BM25 contributed *nothing* for Arabic,
   Hindi, Russian, Chinese — any non-Latin script — silently, no error,
   just quietly worse retrieval. Fixed: switched to `\w+`, which is
   Unicode-aware in Python 3 and correctly tokenizes Arabic, Cyrillic,
   and most other scripts. Verified directly: same Arabic string now
   tokenizes into 8 real words. Tested end-to-end
   (`test_multilingual_retrieval.py`): BM25 now finds the right Arabic
   chapter for an Arabic keyword query. **Known remaining limitation,
   not hidden**: Devanagari-based scripts (Hindi, Marathi, etc.) still
   tokenize imperfectly because of combining/conjunct characters — much
   better than zero, not perfect. CJK languages (Chinese/Japanese/Korean)
   need proper word segmentation (e.g. `jieba` for Chinese), which a
   regex fix can't provide — not done here.

2. **The embedding model was English-only.** `all-MiniLM-L6-v2` produces
   weak, low-quality semantic vectors for non-English text since it
   wasn't meaningfully trained on it — so even the dense-search half of
   retrieval was compromised for Arabic. Switched to
   `paraphrase-multilingual-MiniLM-L12-v2` (50+ languages, same 384-dim
   output so no schema change). Tradeoff: larger model (~470MB vs ~90MB),
   slightly slower.

3. **The reranker was English-only too.** `cross-encoder/ms-marco-MiniLM-L-6-v2`
   was trained only on English MS MARCO query-passage pairs, so it would
   score Arabic relevance close to randomly. Switched to
   `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, trained on the
   multilingual mMARCO (~100 languages).

4. **Arabic/Urdu/Hebrew would have displayed misaligned even with a
   correct answer** — right-to-left text needs `dir="rtl"` or `dir="auto"`;
   nothing in the UI declared a direction, so the browser defaulted to
   LTR. Added `dir="auto"` to every markdown/text container (answers,
   translations, study content, comparisons, the question input box) —
   the browser auto-detects direction per the actual text now instead of
   assuming LTR.

**Important operational note if you already have documents uploaded**:
swapping the embedding model means old and new vectors live in different,
incompatible embedding spaces. If you're upgrading an existing
deployment rather than starting fresh, delete `backend/chroma_db` and
re-upload your documents — don't just restart the server, since queries
embedded with the new model won't compare meaningfully against
old-model vectors even for English documents.

## Full status against "AI Knowledge Workspace" idea list (this document, again)

This exact document was sent before. A lot has changed since then, so
here's an accurate, item-by-item status — not a repeat of the general
disclaimer, an actual answer for each of the 8 numbered ideas plus the
closing vision:

1. **Learning Memory** ("user forgot Bayes twice, give spaced repetition
   tomorrow") — ✅ built. SM-2 spaced repetition on flashcards, due-cards
   endpoint, tested.
2. **Personal Knowledge Graph** — ✅ built **this pass**, previously not
   done. `POST /mindmap/workspace` merges concepts across every document
   in a workspace into one graph — the same concept in two sources
   becomes one node citing both, not two separate nodes. New this
   session, 4 tests covering source-merging, empty-workspace rejection,
   access control, and malformed-output handling. **Honest scope**: one
   LLM call over a sampled context, not a persistent graph database with
   incremental updates or real entity resolution/relationship typing —
   said plainly in the function's own docstring, not just here.
3. **Adaptive Tutor** ("ask *why* do you think B is correct, become a
   teacher") — ❌ still not built. This needs actual pedagogical dialogue
   design (Socratic questioning strategy, tracking what a *specific*
   wrong answer implies about a misconception), which is a different
   kind of work than API endpoints — not scoped down and built here.
4. **Multi-document reasoning** ("read book + slides + paper + notes,
   combine, answer") — ✅ built. Workspace-scoped chat searches across
   every document in a workspace and answers from all of them together.
5. **Agentic Study** ("analyze → generate quiz → evaluate → detect
   weakness → create plan → remind tomorrow") — **partially** built.
   `POST /agent/auto` genuinely picks its own sequence of tools
   (search/summarize/quiz/flashcards/mindmap) rather than following a
   fixed order — that's the real "agentic" part, tested. What's not
   built: "detect weakness" (would need to grade quiz answers and reason
   about *why* they're wrong) and "remind tomorrow" (needs a
   notification/scheduling system, not just backend logic) — no
   push/email reminder infrastructure exists.
6. **Live Retrieval** (GitHub, Wikipedia, Arxiv, company docs) — ❌ still
   not built. Each is a real, separate connector (auth, rate limits, a
   different retrieval shape than chunked-PDF search) — not attempted.
7. **Citation Verification** ("every sentence → exact page → highlighted
   PDF → confidence") — ✅ built. Citations carry page + text snippet,
   the PDF viewer highlights the actual cited passage (pdf.js text-layer
   match), and there's a confidence score derived from the reranker.
   Honest gap: confidence is a real proxy signal (top reranker score,
   documented as such), not a calibrated probability, and it's a
   document-level match score, not literally "every sentence" individually
   verified.
8. **Interactive PDF** ("ask about Q46, it scrolls, highlights, draws
   arrows, explains beside it") — **partially** built: scroll-to-page and
   highlight-the-cited-passage both work now. Drawing arrows / explaining
   beside the highlighted region is a UI feature nobody explicitly
   scoped and isn't built — noted rather than silently skipped.

**Closing vision** ("AI operating system for personal knowledge," RAG as
one component in a larger system) — the architecture is closer to this
than it was: multi-doc workspaces, teams, live collaboration, chained
and autonomous study tools, spaced repetition, cross-document knowledge
graphs, and verified citations are all real now, not just RAG-over-one-PDF.
What's still missing to fully earn that framing — live external
connectors, real adaptive tutoring, a persistent/incremental knowledge
graph rather than a per-request merge — is the same honest list as
above, not new information.

## PDF viewer professional features — status

The "no scroll, page by page, literally sucks" complaint was accurate —
the viewer was rewritten since to fix that first, and most of the
requested feature list was already built alongside it. Audited every
item against the actual code (not just claimed) before writing this:

- ✅ **Continuous smooth scroll** — was the real complaint, is the real
  fix. Rewrote from prev/next page buttons to a single scrollable
  container with all pages laid out vertically, each page lazily
  rendered via `IntersectionObserver` only when it's near the viewport
  (not all pages rendered upfront — that would be slow/memory-heavy for
  long PDFs).
- ✅ **Search inside PDF (Ctrl+F)** — intercepts Ctrl/Cmd+F to open an
  in-document search instead of the browser's own, searches extracted
  text across all pages, next/prev match navigation, highlights and
  scrolls to each match.
- ✅ **Thumbnail sidebar** — lazy-rendered low-res page thumbnails,
  click to jump.
- ✅ **Bookmarks/Outline** — reads the PDF's embedded outline/table of
  contents (`pdfDoc.getOutline()`) if it has one, click to jump. (If the
  PDF has no embedded outline, this correctly shows "No bookmarks in
  this PDF" rather than fabricating one.)
- ✅ **Highlight answer and auto-scroll** — already existed, still works
  with the new continuous-scroll layout.
- ✅ **Click citation → open exact location** — same as above, adapted
  to scroll-to instead of page-switch.
- ✅ **Text selection → "Ask AI about selected text"** — select text in
  the PDF, a popover offers "Ask AI" (prefills the chat input) or "Add
  note."
- ✅ **Persistent annotations** — selecting text and choosing "Add note"
  saves a highlight + note tied to the exact quoted text and its
  position on the page, backed by a real `Annotation` model and CRUD
  API, tested.
- ✅ **Notes attached to PDF** — same model covers freeform notes too; a
  Notes sidebar tab lists all of them, click to jump to the note's page.
- ✅ **Split view (Chat | PDF)** — already existed (side-by-side grid
  layout), confirmed still working.
- ✅ **Multi-PDF tabs** — this was the one genuine gap found during
  audit: the state for tracking open tabs existed in the code but
  nothing ever populated it or rendered a tab bar, so it silently did
  nothing. Fixed: selecting a document now opens it as a tab, a tab bar
  appears once more than one is open, click to switch, ✕ to close.

**Honest limitations, not hidden:**
- Annotations store a normalized (x%, y%) anchor point for the note
  marker, not a resizable/draggable highlight rectangle — good enough to
  mark and reopen a note, not a full annotation editor with shapes or
  freehand drawing.
- Thumbnails and search both operate per-page as pages get rendered;
  for a genuinely huge PDF (many hundreds of pages), initial search
  across not-yet-visited pages will lazily render them to extract text,
  which takes a moment the first time — not instant like a pre-indexed
  search would be.
- I cannot visually confirm pixel-perfect scroll smoothness or exact
  thumbnail rendering from this sandbox (no browser available here) —
  the build compiles clean and the logic is sound on read-through, but
  test the actual feel yourself before fully trusting it.

## Multi-source ingestion: images, websites, GitHub

Audited this before building: the backend was already fully built and
tested (website ingestion with real SSRF protection including a DNS
rebinding test, GitHub single-file ingestion, and scan-to-document OCR
persistence) — but **the frontend had zero wiring for any of it**. That
was the actual gap closed this pass.

- ✅ **Website ingestion** — paste a URL, it fetches the page and extracts
  the readable article content (`trafilatura`, strips nav/ads/boilerplate),
  ingests it through the same chunk/embed/store pipeline as a PDF. Real
  SSRF guardrails: rejects localhost, private/loopback/link-local IP
  ranges, and cloud metadata endpoints, resolved via actual DNS lookup
  (not just string-matching the hostname, which a DNS-rebinding attack
  would bypass) — re-validated again after redirects too.
- ✅ **GitHub ingestion** — paste a `github.com/owner/repo/blob/branch/path`
  URL, imports that one file (README, docs, source file). Explicitly
  **not** a repo crawler or live-sync connector — one file per import,
  pinned to only github.com/raw.githubusercontent.com as fetch targets.
- ✅ **Image → real document** — Scan & Listen now has a "Save as
  Document" button. Previously OCR was a one-off "read this to me" tool
  that didn't persist anything; now the extracted text goes through the
  same pipeline as everything else, so a scanned page becomes something
  you can Chat/Study/Mind-Map, not just hear read aloud once.
- ✅ Source-type icons in the sidebar (📄 PDF, 🌐 website, 🐙 GitHub, 🖼️
  scanned image) so imported documents are visually distinguishable from
  uploads.

**Found and fixed two real bugs while wiring this:**
- I initially wrote duplicate `ingest_from_url`/`ingest_from_github`/
  image-ingestion functions without checking whether they already
  existed — they did, and were better (saved a real `.txt` file to disk
  rather than my version's empty `file_path`, which would have broken
  file serving). Caught it by grepping for duplicate function names
  before trusting my own new code, deleted mine, kept the originals.
- `UploadPanel.jsx` had a leftover `alert("onChange fired")` firing every
  single time a user selected a file to upload — pure debug leftover,
  removed.

**What's still explicitly out of scope, same reasoning as "Live
Retrieval" earlier in this README**: crawling an entire GitHub repo,
syncing with commit history, or any other multi-file/live connector.
This is deliberately "import one file, one time," not a connector.
