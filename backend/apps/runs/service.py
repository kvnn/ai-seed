import re
import secrets
import shutil
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.logger import logger
from backend.models import Run
from backend.apps.runs.schemas import (
    ApprovalRequest,
    BrandArtifact,
    GeneratedFile,
    ResearchArtifact,
    RetryRequest,
    RunCreateRequest,
    RunResponse,
    SiteArtifact,
)


STATUS_DRAFT = "draft"
STATUS_RESEARCH_READY = "research_ready"
STATUS_BRAND_READY = "brand_ready"
STATUS_SITE_READY = "site_ready"
STATUS_APPROVED = "approved"
STATUS_PUBLISHED = "published"
STATUS_FAILED = "failed"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64] or secrets.token_hex(4)


def _short_id() -> str:
    return secrets.token_urlsafe(6)[:8]


def _domain_label(source_url: Optional[str]) -> str:
    if not source_url:
        return "operator brief"
    parsed = urlparse(source_url)
    return parsed.netloc or source_url


def _style_palette(preferred_style: Optional[str]) -> tuple[list[str], str]:
    style = (preferred_style or "").lower()
    if "luxury" in style:
        return ["#0F172A", "#D4A373", "#F8F3E8"], "measured, polished, confident"
    if "playful" in style:
        return ["#155E75", "#F97316", "#FEF3C7"], "warm, energetic, approachable"
    if "minimal" in style or not style:
        return ["#111827", "#B91C1C", "#F8F1E7"], "clear, grounded, restrained"
    return ["#1F2937", "#2563EB", "#F5F5F4"], "clear, grounded, professional"


class RunService:
    def __init__(self, session: Session):
        self._session = session
        self._output_dir = Path(settings.output_dir)

    def create_run(self, created_by: Optional[str], payload: RunCreateRequest) -> RunResponse:
        publish_slug = payload.publish_slug or _slugify(payload.source_url.host if payload.source_url else payload.brief[:32])
        run = Run(
            id=_short_id(),
            created_by=created_by,
            status=STATUS_DRAFT,
            source_url=str(payload.source_url) if payload.source_url else None,
            brief=payload.brief.strip(),
            preferred_style=payload.preferred_style,
            publish_slug=publish_slug,
            required_facts=payload.required_facts,
            banned_claims=payload.banned_claims,
        )
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)

        logger.info("[runs] created run_id=%s created_by=%s", run.id, created_by)

        return self._rebuild_research(run)

    def list_runs(self, created_by: Optional[str] = None) -> list[RunResponse]:
        stmt: Select[tuple[Run]] = select(Run).order_by(Run.updated_at.desc())
        if created_by:
            stmt = stmt.where(Run.created_by == created_by)
        runs = list(self._session.execute(stmt).scalars().all())
        return [self._to_response(run) for run in runs]

    def get_run(self, run_id: str, created_by: Optional[str] = None, is_admin: bool = False) -> RunResponse:
        run = self._session.get(Run, run_id)
        if not run:
            raise ValueError("run_not_found")
        if not is_admin and run.created_by and created_by != run.created_by:
            raise ValueError("run_not_found")
        return self._to_response(run)

    def approve(self, run_id: str, actor_user_id: str, payload: ApprovalRequest, is_admin: bool = False) -> RunResponse:
        run = self._get_mutable_run(run_id, actor_user_id, is_admin)
        self._append_approval(run, actor_user_id, payload.notes)

        if run.status == STATUS_RESEARCH_READY:
            return self._rebuild_brand(run)
        if run.status == STATUS_BRAND_READY:
            return self._rebuild_site(run)
        if run.status == STATUS_SITE_READY:
            run.status = STATUS_APPROVED
            run.failed_stage = None
            run.last_error = None
            self._session.commit()
            self._session.refresh(run)
            logger.info("[runs] approved run_id=%s", run.id)
            return self._to_response(run)
        raise ValueError("approval_not_allowed")

    def retry(self, run_id: str, actor_user_id: str, payload: RetryRequest, is_admin: bool = False) -> RunResponse:
        run = self._get_mutable_run(run_id, actor_user_id, is_admin)
        stage = payload.stage or self._stage_for_run(run)
        if not stage:
            raise ValueError("retry_not_allowed")
        if stage == "research":
            return self._rebuild_research(run)
        if stage == "brand":
            return self._rebuild_brand(run, clear_site=True)
        return self._rebuild_site(run)

    def publish(self, run_id: str, actor_user_id: str, is_admin: bool = False) -> RunResponse:
        run = self._get_mutable_run(run_id, actor_user_id, is_admin)
        if run.status != STATUS_APPROVED or not run.site_payload:
            raise ValueError("publish_not_allowed")

        preview_dir = self._preview_dir(run.id)
        publish_dir = self._published_dir(run.publish_slug)
        if publish_dir.exists():
            shutil.rmtree(publish_dir)
        publish_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(preview_dir, publish_dir)

        run.status = STATUS_PUBLISHED
        run.published_at = datetime.now(timezone.utc)
        run.published_path = str(publish_dir.resolve())
        run.failed_stage = None
        run.last_error = None
        self._session.commit()
        self._session.refresh(run)

        logger.info("[runs] published run_id=%s publish_slug=%s", run.id, run.publish_slug)

        return self._to_response(run)

    def preview_file_path(self, run_id: str, file_path: str) -> Path:
        run = self._session.get(Run, run_id)
        if not run or not run.site_payload:
            raise ValueError("preview_not_found")
        safe_relative = file_path.strip().lstrip("/").replace("\\", "/")
        candidate = (self._preview_dir(run.id) / safe_relative).resolve()
        preview_root = self._preview_dir(run.id).resolve()
        if not str(candidate).startswith(str(preview_root)):
            raise ValueError("preview_not_found")
        if not candidate.exists():
            raise ValueError("preview_not_found")
        return candidate

    def _get_mutable_run(self, run_id: str, actor_user_id: str, is_admin: bool) -> Run:
        run = self._session.get(Run, run_id)
        if not run:
            raise ValueError("run_not_found")
        if not is_admin and run.created_by and run.created_by != actor_user_id:
            raise ValueError("run_not_found")
        return run

    def _append_approval(self, run: Run, actor_user_id: str, notes: Optional[str]) -> None:
        history = list(run.approval_history or [])
        history.append({
            "stage": self._stage_for_run(run) or "approval",
            "actor_user_id": actor_user_id,
            "notes": notes or "",
        })
        run.approval_history = history

    def _rebuild_research(self, run: Run) -> RunResponse:
        try:
            source_label = _domain_label(run.source_url)
            research = ResearchArtifact(
                summary=(
                    f"This draft is grounded in the operator brief for {source_label}. "
                    f"Use it to confirm scope, audience, and factual constraints before brand work begins."
                ),
                source_label=source_label,
                recommended_audience="prospective customers and partners",
                key_facts=run.required_facts or [run.brief[:160].strip()],
                cautions=run.banned_claims or ["Verify any claims that are not explicitly supplied in the brief."],
            )
            run.research_payload = research.model_dump()
            run.brand_payload = None
            run.site_payload = None
            run.status = STATUS_RESEARCH_READY
            run.failed_stage = None
            run.last_error = None
            self._session.commit()
            self._session.refresh(run)
            logger.info("[runs] research_ready run_id=%s", run.id)
            return self._to_response(run)
        except Exception as exc:
            return self._fail_run(run, "research", exc)

    def _rebuild_brand(self, run: Run, clear_site: bool = True) -> RunResponse:
        try:
            palette, voice = _style_palette(run.preferred_style)
            research = ResearchArtifact(**(run.research_payload or {}))
            brand = BrandArtifact(
                vision=(
                    f"{research.source_label} should feel trustworthy, clear, and easy to act on for "
                    f"{research.recommended_audience}."
                ),
                value=(
                    "Present the offer in plain language, reinforce the approved facts, and make the next step obvious."
                ),
                voice=voice,
                brand_imagery=[
                    "editorial layouts",
                    "clean spacing",
                    "credible photography direction",
                ],
                color_palette_hex=palette,
            )
            run.brand_payload = brand.model_dump()
            if clear_site:
                run.site_payload = None
            run.status = STATUS_BRAND_READY
            run.failed_stage = None
            run.last_error = None
            self._session.commit()
            self._session.refresh(run)
            logger.info("[runs] brand_ready run_id=%s", run.id)
            return self._to_response(run)
        except Exception as exc:
            return self._fail_run(run, "brand", exc)

    def _rebuild_site(self, run: Run) -> RunResponse:
        try:
            research = ResearchArtifact(**(run.research_payload or {}))
            brand = BrandArtifact(**(run.brand_payload or {}))
            title = self._page_title(run, research)
            description = brand.value
            files = self._build_site_files(run, research, brand, title, description)
            site = SiteArtifact(
                title=title,
                description=description,
                entrypoint="index.html",
                files=files,
            )
            run.site_payload = site.model_dump()
            run.status = STATUS_SITE_READY
            run.failed_stage = None
            run.last_error = None
            self._session.commit()
            self._session.refresh(run)
            self._write_preview(run.id, site)
            logger.info("[runs] site_ready run_id=%s", run.id)
            return self._to_response(run)
        except Exception as exc:
            return self._fail_run(run, "site", exc)

    def _fail_run(self, run: Run, stage: str, exc: Exception) -> RunResponse:
        run.status = STATUS_FAILED
        run.failed_stage = stage
        run.last_error = str(exc)
        self._session.commit()
        self._session.refresh(run)
        logger.exception("[runs] failed run_id=%s error=%s", run.id, str(exc))
        return self._to_response(run)

    def _page_title(self, run: Run, research: ResearchArtifact) -> str:
        if run.source_url:
            return research.source_label
        brief_words = run.brief.split()
        return " ".join(brief_words[:6]).strip().title() or "OahuAI Site"

    def _build_site_files(
        self,
        run: Run,
        research: ResearchArtifact,
        brand: BrandArtifact,
        title: str,
        description: str,
    ) -> list[GeneratedFile]:
        facts_html = "".join(f"<li>{escape(fact)}</li>" for fact in run.required_facts)
        cautions_html = "".join(f"<li>{escape(item)}</li>" for item in research.cautions)
        palette = brand.color_palette_hex + ["#111827", "#F8F1E7", "#7C2D12"]
        html_content = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description)}" />
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <p class="eyebrow">Reviewed operator draft</p>
        <h1>{escape(title)}</h1>
        <p class="lede">{escape(run.brief)}</p>
      </section>
      <section class="grid">
        <article class="panel">
          <h2>What this site should communicate</h2>
          <p>{escape(brand.value)}</p>
          <p>{escape(brand.vision)}</p>
        </article>
        <article class="panel">
          <h2>Approved facts</h2>
          <ul>{facts_html or '<li>Add specific facts before publish.</li>'}</ul>
        </article>
        <article class="panel">
          <h2>Voice and tone</h2>
          <p>{escape(brand.voice)}</p>
          <p>{escape(', '.join(brand.brand_imagery))}</p>
        </article>
        <article class="panel">
          <h2>Operator cautions</h2>
          <ul>{cautions_html}</ul>
        </article>
      </section>
    </main>
  </body>
</html>
"""
        css_content = f""":root {{
  --ink: {palette[0]};
  --accent: {palette[1]};
  --paper: {palette[2]};
  --panel: rgba(255, 255, 255, 0.78);
}}

* {{
  box-sizing: border-box;
}}

body {{
  margin: 0;
  font-family: Georgia, 'Times New Roman', serif;
  background:
    radial-gradient(circle at top left, rgba(255,255,255,0.75), transparent 36%),
    linear-gradient(160deg, var(--paper), #f4efe8 55%, #efe6da 100%);
  color: var(--ink);
}}

.shell {{
  max-width: 1040px;
  margin: 0 auto;
  padding: 72px 24px 96px;
}}

.hero {{
  margin-bottom: 40px;
}}

.eyebrow {{
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.8rem;
  color: var(--accent);
}}

h1 {{
  font-size: clamp(2.6rem, 6vw, 5rem);
  line-height: 0.96;
  margin: 0 0 16px;
}}

.lede {{
  max-width: 52rem;
  font-size: 1.12rem;
  line-height: 1.7;
}}

.grid {{
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}}

.panel {{
  padding: 24px;
  border: 1px solid rgba(17, 24, 39, 0.12);
  background: var(--panel);
  backdrop-filter: blur(8px);
  border-radius: 20px;
  box-shadow: 0 18px 60px rgba(17, 24, 39, 0.08);
}}

h2 {{
  margin-top: 0;
  font-size: 1rem;
}}

ul {{
  padding-left: 1.1rem;
}}
"""
        return [
            GeneratedFile(path="index.html", media_type="text/html", content=html_content),
            GeneratedFile(path="styles.css", media_type="text/css", content=css_content),
        ]

    def _write_preview(self, run_id: str, site: SiteArtifact) -> None:
        preview_dir = self._preview_dir(run_id)
        if preview_dir.exists():
            shutil.rmtree(preview_dir)
        preview_dir.mkdir(parents=True, exist_ok=True)
        for file in site.files:
            safe_relative = file.path.strip().lstrip("/").replace("\\", "/")
            target = (preview_dir / safe_relative).resolve()
            if not str(target).startswith(str(preview_dir.resolve())):
                raise ValueError("invalid_preview_path")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file.content, encoding="utf-8")

    def _preview_dir(self, run_id: str) -> Path:
        return self._output_dir / "runs" / run_id / "site"

    def _published_dir(self, publish_slug: str) -> Path:
        return self._output_dir / "published" / publish_slug

    def _stage_for_run(self, run: Run) -> Optional[str]:
        if run.status in {STATUS_DRAFT, STATUS_RESEARCH_READY}:
            return "research"
        if run.status == STATUS_FAILED:
            return run.failed_stage
        if run.status == STATUS_BRAND_READY:
            return "brand"
        if run.status in {STATUS_SITE_READY, STATUS_APPROVED, STATUS_PUBLISHED}:
            return "site"
        return None

    def _next_actions(self, run: Run) -> list[str]:
        if run.status == STATUS_RESEARCH_READY:
            return ["approve_research", "retry_research"]
        if run.status == STATUS_BRAND_READY:
            return ["approve_brand", "retry_brand"]
        if run.status == STATUS_SITE_READY:
            return ["approve_site", "retry_site"]
        if run.status == STATUS_APPROVED:
            return ["publish", "retry_site"]
        if run.status == STATUS_PUBLISHED:
            return ["retry_site"]
        if run.status == STATUS_FAILED:
            stage = run.failed_stage or "research"
            return [f"retry_{stage}"]
        return ["start_research"]

    def _to_response(self, run: Run) -> RunResponse:
        site = SiteArtifact(**run.site_payload) if run.site_payload else None
        preview_url = None
        if site:
            preview_url = f"/preview/runs/{run.id}/site/{site.entrypoint}"
        return RunResponse(
            id=run.id,
            status=run.status,
            source_url=run.source_url,
            brief=run.brief,
            preferred_style=run.preferred_style,
            publish_slug=run.publish_slug,
            required_facts=run.required_facts or [],
            banned_claims=run.banned_claims or [],
            research=ResearchArtifact(**run.research_payload) if run.research_payload else None,
            brand=BrandArtifact(**run.brand_payload) if run.brand_payload else None,
            site=site,
            next_actions=self._next_actions(run),
            preview_url=preview_url,
            published_path=run.published_path,
            failed_stage=run.failed_stage,
            last_error=run.last_error,
            created_at=run.created_at,
            updated_at=run.updated_at,
            published_at=run.published_at,
        )
