import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import settings
from src.core.logging import logger
from src.core.rate_limit import RateLimitMiddleware
from src.core.metrics import MetricsMiddleware, router as metrics_router

from src.db.database import engine, Base, SessionLocal

from src.api.health import router as health_router
from src.api.auth import router as auth_router
from src.api.document import router as document_router
from src.api.chat import router as chat_router
from src.api.history import router as history_router
from src.api.scan import router as scan_router
from src.api.study import router as study_router
from src.api.compare import router as compare_router
from src.api.mindmap import router as mindmap_router
from src.api.agent import router as agent_router
from src.api.team import router as team_router
from src.api.workspace import router as workspace_router
from src.api.ws import router as ws_router
from src.api.activity import router as activity_router
from src.api.flashcard import router as flashcard_router
from src.api.annotation import router as annotation_router
from src.api.upload import router as upload_router  # Universal upload API
from src.api.knowledge import router as knowledge_router  # Knowledge Intelligence API
from src.api.interaction import router as interaction_router  # Knowledge Interaction API
from src.api.research import router as research_router  # Research Operating System API
from src.api.multi_agent import router as multi_agent_router  # Multi-Agent System API
from src.api.multilingual import router as multilingual_router  # Multilingual Intelligence API
from src.autonomous.api.autonomous import router as autonomous_router  # Autonomous Learning System API
from src.api.integration import router as integration_router  # Autonomous Integration & Activation Layer
from src.api.work_intelligence import router as work_intelligence_router  # AI Work Intelligence Layer
from src.api.execution import router as execution_router  # AI Execution Layer
from src.api.events import router as events_router  # Real-time Event Stream

# New API scaffolds for future modules
from src.api.analytics import router as analytics_router
from src.api.jobs import router as jobs_router
from src.api.exam import router as exam_router
from src.api.video import router as video_router
from src.api.math import router as math_router
from src.api.orchestration import router as orchestration_router

from src.models.user import User
from src.models.document import Document
from src.models.chat import Chat
from src.models.team import Team, TeamMembership, TeamInvite
from src.models.workspace import Workspace
from src.models.quiz_attempt import QuizAttempt
from src.models.flashcard import Flashcard
from src.models.annotation import Annotation

from src.core.security import hash_password

from contextlib import asynccontextmanager


# ============================================================================
# Enterprise Architecture Global Instances
# ============================================================================

# These are set in lifespan() after app creation
orchestrator = None
task_dispatcher = None
workflow_engine = None
event_emitter = None


def _initialize_enterprise_components():
    """
    Initialize enterprise architecture components.
    
    Sets up:
    - Master Orchestrator with registered agents
    - Task Dispatcher for async task execution
    - Workflow Engine with predefined templates
    - Event Emitter for real-time updates
    """
    global orchestrator, task_dispatcher, workflow_engine, event_emitter
    
    from src.enterprise.orchestrator.master import MasterOrchestrator
    from src.enterprise.dispatcher.task_dispatcher import TaskDispatcher
    from src.enterprise.workflows.engine import WorkflowEngine
    from src.enterprise.agents.base_wrappers import (
        ChatAgent, DocumentAgent, FlashcardAgent,
        MindmapAgent, StudyPackAgent, CompareAgent, ScanAgent
    )
    from src.core.event_emitter import get_event_emitter
    from src.core.ws_manager import manager
    
    # Initialize components
    orchestrator = MasterOrchestrator()
    task_dispatcher = TaskDispatcher()
    workflow_engine = WorkflowEngine()
    event_emitter = get_event_emitter()
    event_emitter.set_ws_manager(manager)
    
    # Register existing functionality as agents
    orchestrator.register_agent(ChatAgent())
    orchestrator.register_agent(DocumentAgent())
    orchestrator.register_agent(FlashcardAgent())
    orchestrator.register_agent(MindmapAgent())
    orchestrator.register_agent(StudyPackAgent())
    orchestrator.register_agent(CompareAgent())
    orchestrator.register_agent(ScanAgent())
    
    logger.info("Enterprise components initialized with %d agents", len(orchestrator.registry))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    logger.info("Database connected successfully.")

    _bootstrap_admin_if_configured()
    
    # Initialize enterprise components
    _initialize_enterprise_components()
    
    # Start event emitter
    if event_emitter:
        await event_emitter.start()
    
    # Start task dispatcher worker
    if task_dispatcher:
        await task_dispatcher.start()
    
    # Initialize orchestrator (starts agents)
    if orchestrator:
        await orchestrator.initialize()
    
    logger.info("%s started successfully.", settings.APP_NAME)

    yield
    
    # Cleanup
    if event_emitter:
        await event_emitter.stop()
    if orchestrator:
        await orchestrator.shutdown()
    if task_dispatcher:
        await task_dispatcher.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Rate limiting first (cheapest check, rejects abuse before any real work),
# then request metrics.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(MetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(history_router)
app.include_router(scan_router)
app.include_router(study_router)
app.include_router(compare_router)
app.include_router(mindmap_router)
app.include_router(agent_router)
app.include_router(team_router)
app.include_router(workspace_router)
app.include_router(ws_router)
app.include_router(activity_router)
app.include_router(flashcard_router)
app.include_router(annotation_router)
app.include_router(upload_router)  # Universal upload API
app.include_router(knowledge_router)  # Knowledge Intelligence API
app.include_router(interaction_router)  # Knowledge Interaction API
app.include_router(research_router)  # Research Operating System API
app.include_router(multi_agent_router)  # Multi-Agent System API
app.include_router(multilingual_router)  # Multilingual Intelligence API
app.include_router(autonomous_router)  # Autonomous Learning System API
app.include_router(integration_router)  # Autonomous Integration & Activation Layer
app.include_router(work_intelligence_router)  # AI Work Intelligence Layer
app.include_router(execution_router)  # AI Execution Layer
app.include_router(events_router)  # Real-time Event Stream
app.include_router(metrics_router)

# ============================================================================
# Future Module Scaffolds (ready for implementation)
# ============================================================================
app.include_router(orchestration_router)  # Agent orchestration API
app.include_router(analytics_router)       # Analytics features
app.include_router(jobs_router)            # Job hunting features
app.include_router(exam_router)            # Exam preparation features
app.include_router(video_router)            # Video processing features
app.include_router(math_router)           # Math/science features

# --- Optional: serve the built frontend from this same process ---------
# The two-container (nginx + backend) setup in docker-compose.yml is the
# default. This block additionally supports a single-container deployment
# (see docker/Dockerfile.single + README "Free deployment on Hugging Face
# Spaces") where the frontend's build output is copied into ./static and
# FastAPI serves it directly -- no nginx needed, which matters on free
# hosts that only let you run one process/container.
_STATIC_DIR = Path(os.environ.get("STATIC_DIR") or (Path(__file__).resolve().parent.parent / "static"))

if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Let real API routes 404 normally instead of being swallowed by
        # this catch-all -- it only ever serves index.html for unknown
        # (i.e. frontend-router) paths, mirroring nginx's `try_files`.
        candidate = _STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_STATIC_DIR / "index.html")


def _bootstrap_admin_if_configured():
    """
    Creates the first admin account from env vars, ONLY if no admin exists
    yet. This solves the chicken-and-egg problem of RBAC-protected admin
    provisioning endpoints (Section: Module 1 - Roles).
    """
    if not settings.BOOTSTRAP_ADMIN_EMAIL or not settings.BOOTSTRAP_ADMIN_PASSWORD:
        return

    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == "admin").first()
        if existing_admin:
            return

        existing_user = (
            db.query(User)
            .filter(User.email == settings.BOOTSTRAP_ADMIN_EMAIL)
            .first()
        )
        if existing_user:
            existing_user.role = "admin"
            db.commit()
            logger.info("Promoted existing user to admin via bootstrap config.")
            return

        admin = User(
            full_name="Administrator",
            email=settings.BOOTSTRAP_ADMIN_EMAIL,
            hashed_password=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
            role="admin",
        )
        db.add(admin)
        db.commit()
        logger.info("Bootstrap admin account created.")
    finally:
        db.close()
