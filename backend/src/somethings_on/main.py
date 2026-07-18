from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from agents import set_default_openai_key, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel
from chatkit.server import NonStreamingResult, StreamingResult
from fastapi import FastAPI, File, Header, HTTPException, Query, Request, UploadFile, status
from fastapi import Path as ApiPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from openai import AsyncOpenAI
from pydantic import ValidationError

from .casting import CastingPresetCatalog, CastingPresetNotFoundError
from .chat_server import DesignChatServer
from .chat_store import SQLiteChatStore
from .config import Settings, get_settings
from .demo_seed import DEVDAY_PROJECT_ID, DevDayDemoSeeder
from .design_store import (
    AssetNotFoundError,
    DesignVersionNotFoundError,
    ProjectNotFoundError,
    SQLiteDesignStore,
)
from .image_service import (
    CanonicalDesignAssetRequired,
    DesignImageService,
    GarmentPreservationAssessor,
    ImageGenerationUnavailable,
    ImageProvider,
    InvalidImageError,
    OpenAIImageProvider,
    RevisionBaseAssetRequired,
)
from .models import (
    AssetRecord,
    CastingPresetCollection,
    DesignRevisionCreateInput,
    DesignVersionRecord,
    HealthResponse,
    LinkReferenceInput,
    LinkReferenceRecord,
    PresentationCreateInput,
    PresentationRenderRecord,
    ProjectSeedInput,
    ProjectSnapshot,
)
from .product_catalog import ProductCatalog, ProductCatalogError
from .product_image_cache import ProductImageNotFoundError
from .reference_catalog import ReferenceCatalog, ReferenceCatalogError

ProjectId = Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
AssetId = Annotated[str, ApiPath(pattern=r"^ast_[a-f0-9]{12}$")]


def create_app(
    settings: Settings | None = None,
    *,
    image_provider: ImageProvider | None = None,
    preservation_assessor: GarmentPreservationAssessor | None = None,
) -> FastAPI:
    runtime = settings or get_settings()
    api_key = runtime.api_key_value
    agent_model = runtime.agent_model
    if api_key:
        set_default_openai_key(api_key, use_for_tracing=False)
        # Bind ChatKit's agent model to this app's key explicitly. The Agents SDK caches its
        # process-wide default client, so relying on environment discovery can retain a stale key
        # when the local service is restarted from a long-lived development process.
        agent_model = OpenAIResponsesModel(
            model=runtime.agent_model,
            openai_client=AsyncOpenAI(api_key=api_key),
        )
        if image_provider is None:
            openai_provider = OpenAIImageProvider(
                api_key,
                runtime.image_model,
                assessment_model=runtime.agent_model,
            )
            provider = openai_provider
            assessor = preservation_assessor or openai_provider
        else:
            provider = image_provider
            assessor = preservation_assessor
    else:
        set_tracing_disabled(True)
        provider = image_provider
        assessor = preservation_assessor

    chat_store = SQLiteChatStore(runtime.database_path)
    design_store = SQLiteDesignStore(runtime.database_path)
    casting_catalog = CastingPresetCatalog.load(runtime.casting_presets_path)
    reference_catalog = ReferenceCatalog(
        db_path=runtime.reference_catalog_database_path,
        manifest_path=runtime.reference_catalog_manifest_path,
    )
    product_catalog = ProductCatalog(
        db_path=runtime.reference_catalog_database_path,
        manifest_path=runtime.product_catalog_manifest_path,
    )
    image_service = DesignImageService(
        store=design_store,
        asset_root=runtime.asset_path,
        provider=provider,
        image_model=runtime.image_model,
        casting_catalog=casting_catalog,
        preservation_assessor=assessor,
    )
    devday_demo_seeder = DevDayDemoSeeder(
        store=design_store,
        asset_root=runtime.asset_path,
    )
    chatkit_server = DesignChatServer(
        chat_store=chat_store,
        design_store=design_store,
        image_service=image_service,
        agent_model=agent_model,
        agent_ready=bool(api_key),
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        await chat_store.initialize()
        await design_store.initialize()
        await image_service.initialize()
        await devday_demo_seeder.ensure_seeded()
        await asyncio.to_thread(reference_catalog.build)
        await asyncio.to_thread(product_catalog.build)
        application.state.settings = runtime
        application.state.design_store = design_store
        application.state.image_service = image_service
        application.state.devday_demo_seeder = devday_demo_seeder
        application.state.chatkit_server = chatkit_server
        application.state.reference_catalog = reference_catalog
        application.state.product_catalog = product_catalog
        yield

    app = FastAPI(
        title="SOMETHINGS-ON API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[runtime.allowed_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Accept", "Content-Type", "X-Requested-With"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            chatkit_ready=bool(api_key and runtime.chatkit_domain_key),
            chatkit_domain_key=runtime.chatkit_domain_key,
            agent_model=runtime.agent_model,
            image_model=runtime.image_model,
        )

    @app.get("/api/casting-presets", response_model=CastingPresetCollection)
    async def get_casting_presets() -> CastingPresetCollection:
        return casting_catalog.collection

    @app.get("/api/references")
    async def get_references(
        query: str = "",
        limit: Annotated[int, Query(ge=1, le=30)] = 30,
        label_ids: Annotated[list[str] | None, Query()] = None,
        categories: Annotated[list[str] | None, Query()] = None,
        object_types: Annotated[list[str] | None, Query()] = None,
    ) -> list[dict[str, object]]:
        try:
            return await asyncio.to_thread(
                reference_catalog.search,
                query,
                limit,
                label_ids=label_ids,
                categories=categories,
                object_types=object_types,
            )
        except (ReferenceCatalogError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/inspiration")
    async def get_inspiration(
        query: str = "",
        limit: Annotated[int, Query(ge=1, le=30)] = 30,
        brands: Annotated[list[str] | None, Query()] = None,
        categories: Annotated[list[str] | None, Query()] = None,
        object_types: Annotated[list[str] | None, Query()] = None,
    ) -> list[dict[str, object]]:
        try:
            return await asyncio.to_thread(
                product_catalog.search,
                query,
                limit,
                brands=brands,
                categories=categories,
                object_types=object_types,
            )
        except (ProductCatalogError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/inspiration/facets")
    async def get_inspiration_facets() -> dict[str, object]:
        try:
            return await asyncio.to_thread(product_catalog.facets)
        except ProductCatalogError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/inspiration/images/{product_id}", response_class=FileResponse)
    async def get_inspiration_image(
        product_id: Annotated[
            str,
            ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"),
        ],
    ) -> FileResponse:
        try:
            cached = await asyncio.to_thread(product_catalog.resolve_image, product_id)
        except ProductImageNotFoundError as error:
            raise HTTPException(status_code=404, detail="Product image not found") from error
        return FileResponse(
            path=cached.path,
            media_type=cached.media_type,
            headers={
                "Cache-Control": "private, max-age=31536000, immutable",
                "ETag": f'"{cached.sha256}"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/api/projects/{project_id}", response_model=ProjectSnapshot)
    async def get_project(project_id: ProjectId) -> ProjectSnapshot:
        try:
            return await design_store.get_project(project_id)
        except ProjectNotFoundError as error:
            raise HTTPException(status_code=404, detail="Project not found") from error

    @app.put("/api/projects/{project_id}", response_model=ProjectSnapshot)
    async def put_project(project_id: ProjectId, seed: ProjectSeedInput) -> ProjectSnapshot:
        project = await design_store.upsert_project(project_id, seed)
        if project_id == DEVDAY_PROJECT_ID:
            return await devday_demo_seeder.ensure_seeded()
        return project

    @app.post(
        "/api/projects/{project_id}/versions",
        response_model=DesignVersionRecord,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_design_version(
        project_id: ProjectId,
        revision: DesignRevisionCreateInput,
    ) -> DesignVersionRecord:
        try:
            project = await design_store.get_project(project_id)
            base_version = (
                await design_store.get_design_version(project_id, revision.base_version_id)
                if revision.base_version_id is not None
                else project.current_version
            )
            if revision.base_version_id is not None and (
                base_version is None or base_version.asset_id is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "The selected design version has no raster to edit. Generate the first "
                        "design without a base version."
                    ),
                )
            if base_version is not None and base_version.asset_id is not None:
                try:
                    await image_service.resolve_asset(base_version.asset_id)
                except (AssetNotFoundError, InvalidImageError) as error:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="The selected design raster is unavailable. Choose another version.",
                    ) from error
            return await image_service.create_revision(
                project_id=project_id,
                requested_change=revision.requested_change,
                preserve=revision.preserve,
                avoid=revision.avoid,
                base_version_id=revision.base_version_id,
            )
        except ProjectNotFoundError as error:
            raise HTTPException(status_code=404, detail="Project not found") from error
        except DesignVersionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Design version not found") from error
        except RevisionBaseAssetRequired as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except InvalidImageError as error:
            raise HTTPException(
                status_code=503,
                detail=("The new image could not be read. The prior version is unchanged."),
            ) from error
        except ImageGenerationUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get(
        "/api/projects/{project_id}/presentations",
        response_model=list[PresentationRenderRecord],
    )
    async def list_presentations(project_id: ProjectId) -> list[PresentationRenderRecord]:
        try:
            project = await design_store.get_project(project_id)
        except ProjectNotFoundError as error:
            raise HTTPException(status_code=404, detail="Project not found") from error
        return project.presentations

    @app.post(
        "/api/projects/{project_id}/presentations",
        response_model=PresentationRenderRecord,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_presentation(
        project_id: ProjectId,
        presentation: PresentationCreateInput,
    ) -> PresentationRenderRecord:
        try:
            return await image_service.create_presentation(
                project_id=project_id,
                request=presentation,
            )
        except ProjectNotFoundError as error:
            raise HTTPException(status_code=404, detail="Project not found") from error
        except DesignVersionNotFoundError as error:
            raise HTTPException(status_code=404, detail="Design version not found") from error
        except CastingPresetNotFoundError as error:
            raise HTTPException(status_code=404, detail="Casting preset not found") from error
        except CanonicalDesignAssetRequired as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ImageGenerationUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post(
        "/api/projects/{project_id}/references",
        response_model=AssetRecord,
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_reference(
        project_id: ProjectId,
        file: Annotated[UploadFile, File()],
    ) -> AssetRecord:
        content = await file.read(runtime.max_upload_bytes + 1)
        await file.close()
        if len(content) > runtime.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Image exceeds the upload limit")
        try:
            return await image_service.ingest_reference(
                project_id=project_id,
                content=content,
                content_type=file.content_type or "application/octet-stream",
                original_name=file.filename or "reference",
            )
        except InvalidImageError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post(
        "/api/projects/{project_id}/reference-links",
        response_model=LinkReferenceRecord,
        status_code=status.HTTP_201_CREATED,
    )
    async def add_reference_link(
        project_id: ProjectId,
        reference: LinkReferenceInput,
    ) -> LinkReferenceRecord:
        url = str(reference.url)
        hostname = urlparse(url).hostname or "Reference link"
        return await design_store.add_link_reference(
            project_id,
            url,
            reference.label or hostname.removeprefix("www."),
        )

    @app.get("/api/assets/{asset_id}", response_class=FileResponse)
    async def get_asset(asset_id: AssetId) -> FileResponse:
        try:
            record, _ = await design_store.get_asset_location(asset_id)
            path = await image_service.resolve_asset(asset_id)
        except (AssetNotFoundError, InvalidImageError) as error:
            raise HTTPException(status_code=404, detail="Asset not found") from error
        return FileResponse(
            path=Path(path),
            media_type=record.mime_type,
            headers={"Cache-Control": "private, max-age=31536000, immutable"},
        )

    @app.post("/api/projects/{project_id}/chatkit")
    async def chatkit_endpoint(
        project_id: ProjectId,
        request: Request,
        base_version_id: Annotated[
            str | None,
            Query(pattern=r"^ver_[a-f0-9]{12}$"),
        ] = None,
        selected_version_id: Annotated[
            str | None,
            Header(
                alias="X-Somethings-On-Base-Version-Id",
                pattern=r"^ver_[a-f0-9]{12}$",
            ),
        ] = None,
    ) -> Response:
        if (
            base_version_id is not None
            and selected_version_id is not None
            and base_version_id != selected_version_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Conflicting design version selection",
            )
        base_version_id = selected_version_id or base_version_id
        if base_version_id is not None:
            try:
                base_version = await design_store.get_design_version(
                    project_id,
                    base_version_id,
                )
            except DesignVersionNotFoundError as error:
                raise HTTPException(
                    status_code=404,
                    detail="Design version not found",
                ) from error
            if base_version.asset_id is None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "The selected design version has no raster to edit. Generate the first "
                        "design without a base version."
                    ),
                )
        try:
            result = await chatkit_server.process(
                await request.body(),
                {
                    "project_id": project_id,
                    "request_id": request.headers.get("x-request-id", "local"),
                    "base_version_id": base_version_id,
                },
            )
        except ValidationError as error:
            raise HTTPException(status_code=400, detail="Invalid ChatKit request") from error

        if isinstance(result, StreamingResult):
            return StreamingResponse(
                result,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache, no-transform",
                    "X-Accel-Buffering": "no",
                },
            )
        if isinstance(result, NonStreamingResult):
            return Response(content=result.json, media_type="application/json")
        raise HTTPException(status_code=500, detail="Unexpected ChatKit response")

    return app


app = create_app()
