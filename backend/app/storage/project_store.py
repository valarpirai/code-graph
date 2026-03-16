# app/storage/project_store.py
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from app.models.project import ProjectMeta, ProjectStatus

class ProjectStore:
    def __init__(self, data_dir: str = "/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _project_dir(self, project_id: str) -> Path:
        return self.data_dir / project_id

    def _meta_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "project.json"

    def save(self, meta: ProjectMeta) -> None:
        project_dir = self._project_dir(meta.id)
        project_dir.mkdir(parents=True, exist_ok=True)
        with open(self._meta_path(meta.id), "w") as f:
            f.write(meta.model_dump_json(indent=2))

    def load(self, project_id: str) -> ProjectMeta:
        path = self._meta_path(project_id)
        if not path.exists():
            raise KeyError(f"Project '{project_id}' not found")
        with open(path) as f:
            return ProjectMeta.model_validate_json(f.read())

    def list_all(self) -> list[ProjectMeta]:
        projects = []
        for project_dir in self.data_dir.iterdir():
            if project_dir.is_dir():
                meta_path = project_dir / "project.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        projects.append(ProjectMeta.model_validate_json(f.read()))
        return projects

    def delete(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)

    def update_status(
        self,
        project_id: str,
        status: ProjectStatus,
        error_message: Optional[str] = None,
    ) -> None:
        meta = self.load(project_id)
        meta.status = status
        meta.error_message = error_message
        if status == ProjectStatus.READY:
            meta.last_indexed = datetime.now(timezone.utc)
        self.save(meta)

    def source_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "source"

    def wiki_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "wiki"

    def graph_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "graph.ttl"
