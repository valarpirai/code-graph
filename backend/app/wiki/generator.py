import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from rdflib import Graph

from app.wiki import sparql_queries as Q

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _rows_to_dicts(result) -> list[dict]:
    """Convert SPARQL ResultRow objects to plain dicts keyed by variable name."""
    return [
        {str(var): (str(row[var]) if row[var] is not None else None) for var in row.labels}
        for row in result
    ]


class WikiGenerator:
    def __init__(self, project: Any, graph: Graph, output_dir: Path):
        self.project = project
        self.graph = graph
        self.output_dir = Path(output_dir)
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape([]),
            keep_trailing_newline=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """Clear output dir, then write all wiki files."""
        self._clear_output_dir()
        self._write_index()
        self._write_classes()
        self._write_functions()
        self._write_modules()

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _clear_output_dir(self) -> None:
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "classes").mkdir()
        (self.output_dir / "functions").mkdir()
        (self.output_dir / "modules").mkdir()

    def _render(self, template_name: str, **context: Any) -> str:
        tmpl = self._env.get_template(template_name)
        return tmpl.render(**context)

    def _write(self, rel_path: str, content: str) -> None:
        dest = self.output_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Page writers
    # ------------------------------------------------------------------

    def _write_index(self) -> None:
        stats_rows = _rows_to_dicts(self.graph.query(Q.PROJECT_STATS))
        stats = stats_rows[0] if stats_rows else {}

        lang_rows = _rows_to_dicts(self.graph.query(Q.PROJECT_LANGUAGES))
        languages = [r["language"] for r in lang_rows]

        module_rows = _rows_to_dicts(self.graph.query(Q.TOP_LEVEL_MODULES))
        modules = []
        for r in module_rows:
            name = r.get("name") or r.get("module", "").rsplit("/", 1)[-1]
            modules.append({"name": name, "filePath": r.get("filePath", "")})

        cluster_rows = _rows_to_dicts(self.graph.query(Q.CLUSTER_SUMMARY))

        content = self._render(
            "index.md.j2",
            project=self.project,
            stats=stats,
            languages=languages,
            modules=modules,
            clusters=cluster_rows,
        )
        self._write("index.md", content)

    def _write_classes(self) -> None:
        class_rows   = _rows_to_dicts(self.graph.query(Q.CLASS_DETAILS))
        inherit_rows = _rows_to_dicts(self.graph.query(Q.CLASS_INHERITANCE))
        iface_rows   = _rows_to_dicts(self.graph.query(Q.CLASS_INTERFACES))
        mixin_rows   = _rows_to_dicts(self.graph.query(Q.CLASS_MIXINS))
        field_rows   = _rows_to_dicts(self.graph.query(Q.CLASS_FIELDS))
        method_rows  = _rows_to_dicts(self.graph.query(Q.CLASS_METHODS))
        dep_rows     = _rows_to_dicts(self.graph.query(Q.CLASS_DEPENDENCIES))
        cluster_rows = _rows_to_dicts(self.graph.query(Q.CLASS_CLUSTER))

        for cls in class_rows:
            cls_uri = cls.get("cls", "")
            name    = cls.get("name", "UnknownClass")

            inheritance = [r["parent"] for r in inherit_rows if r.get("cls") == cls_uri]
            interfaces  = [r["iface"]  for r in iface_rows   if r.get("cls") == cls_uri]
            mixins      = [r["mixin"]  for r in mixin_rows    if r.get("cls") == cls_uri]
            fields      = [r for r in field_rows  if r.get("cls") == cls_uri]
            methods     = [r for r in method_rows if r.get("cls") == cls_uri]
            deps        = [r for r in dep_rows    if r.get("cls") == cls_uri]
            cluster_hit = next((r for r in cluster_rows if r.get("cls") == cls_uri), None)

            content = self._render(
                "class.md.j2",
                cls=cls,
                inheritance=inheritance,
                interfaces=interfaces,
                mixins=mixins,
                fields=fields,
                methods=methods,
                callers=[],
                dependencies=deps,
                cluster=cluster_hit,
            )
            self._write(f"classes/{name}.md", content)

    def _write_functions(self) -> None:
        fn_rows      = _rows_to_dicts(self.graph.query(Q.STANDALONE_FUNCTIONS))
        param_rows   = _rows_to_dicts(self.graph.query(Q.FUNCTION_PARAMETERS))
        var_rows     = _rows_to_dicts(self.graph.query(Q.FUNCTION_LOCAL_VARS))
        callee_rows  = _rows_to_dicts(self.graph.query(Q.FUNCTION_CALLEES))
        role_rows    = _rows_to_dicts(self.graph.query(Q.FUNCTION_FRAMEWORK_ROLE))
        cluster_rows = _rows_to_dicts(self.graph.query(Q.FUNCTION_CLUSTER))

        for fn in fn_rows:
            fn_uri   = fn.get("fn", "")
            name     = fn.get("name", "unknown")
            mod_uri  = fn.get("module", "")
            mod_name = mod_uri.rsplit("/", 1)[-1] if mod_uri else "nomodule"

            params      = [r for r in param_rows   if r.get("fn") == fn_uri]
            local_vars  = [r for r in var_rows      if r.get("fn") == fn_uri]
            callees     = [r for r in callee_rows   if r.get("fn") == fn_uri]
            role_hit    = next((r for r in role_rows    if r.get("fn") == fn_uri), None)
            cluster_hit = next((r for r in cluster_rows if r.get("fn") == fn_uri), None)

            content = self._render(
                "function.md.j2",
                fn=fn,
                parameters=params,
                local_vars=local_vars,
                callers=[],
                callees=callees,
                framework_role=role_hit,
                cluster=cluster_hit,
            )
            self._write(f"functions/{mod_name}_{name}.md", content)

    def _write_modules(self) -> None:
        module_rows = _rows_to_dicts(self.graph.query(Q.MODULE_DETAILS))
        class_rows  = _rows_to_dicts(self.graph.query(Q.MODULE_CLASSES))
        fn_rows     = _rows_to_dicts(self.graph.query(Q.MODULE_FUNCTIONS))
        const_rows  = _rows_to_dicts(self.graph.query(Q.MODULE_CONSTANTS))
        import_rows = _rows_to_dicts(self.graph.query(Q.MODULE_IMPORTS))

        for mod in module_rows:
            mod_uri   = mod.get("module", "")
            name      = mod.get("name", "unknown")

            classes   = [r for r in class_rows  if r.get("module") == mod_uri]
            functions = [r for r in fn_rows      if r.get("module") == mod_uri]
            constants = [r for r in const_rows   if r.get("module") == mod_uri]
            imports   = [r for r in import_rows  if r.get("module") == mod_uri]

            content = self._render(
                "module.md.j2",
                module=mod,
                classes=classes,
                functions=functions,
                constants=constants,
                imports=imports,
            )
            self._write(f"modules/{name}.md", content)
