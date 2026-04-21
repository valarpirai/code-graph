# app/storage/project_store.py
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from app.models.project import ProjectMeta, ProjectStatus

_INDEX_FILE = "projects.json"


class ProjectStore:
    def __init__(self, data_dir: str = "/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def _index_path(self) -> Path:
        return self.data_dir / _INDEX_FILE

    def _load_index(self) -> dict[str, dict]:
        if not self._index_path.exists():
            return {}
        with open(self._index_path) as f:
            return json.load(f)

    def _write_index(self, index: dict[str, dict]) -> None:
        with open(self._index_path, "w") as f:
            json.dump(index, f, indent=2, default=str)

    def _project_dir(self, project_id: str) -> Path:
        return self.data_dir / project_id

    def _meta_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "project.json"

    def save(self, meta: ProjectMeta) -> None:
        project_dir = self._project_dir(meta.id)
        project_dir.mkdir(parents=True, exist_ok=True)
        with open(self._meta_path(meta.id), "w") as f:
            f.write(meta.model_dump_json(indent=2))
        # Keep index in sync
        index = self._load_index()
        index[meta.id] = json.loads(meta.model_dump_json())
        self._write_index(index)

    def load(self, project_id: str) -> ProjectMeta:
        path = self._meta_path(project_id)
        if not path.exists():
            raise KeyError(f"Project '{project_id}' not found")
        with open(path) as f:
            return ProjectMeta.model_validate_json(f.read())

    def list_all(self) -> list[ProjectMeta]:
        index = self._load_index()
        if index:
            return [ProjectMeta.model_validate(v) for v in index.values()]
        # Fallback: scan dirs and build the index (handles pre-existing data)
        projects: list[ProjectMeta] = []
        for project_dir in self.data_dir.iterdir():
            if project_dir.is_dir():
                meta_path = project_dir / "project.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        meta = ProjectMeta.model_validate_json(f.read())
                    projects.append(meta)
        if projects:
            index = {p.id: json.loads(p.model_dump_json()) for p in projects}
            self._write_index(index)
        return projects

    def delete(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)
        index = self._load_index()
        index.pop(project_id, None)
        self._write_index(index)

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
