from pathlib import Path
from .parsing import get_parser
from .parsing.config_parsers import parse_config_file
from .parsing.entry_point_scorer import score_entry_point
from .rdf.builder import RDFBuilder
from .rdf.graph_store import save_graph


class Indexer:
    async def run(self, project_id: str, source_dir: Path, data_dir: Path, notifier=None):
        parsed_files = []
        paths = [p for p in source_dir.rglob("*") if p.is_file()]

        for i, path in enumerate(paths):
            parser = get_parser(path.suffix)
            if parser is not None:
                try:
                    source = path.read_text(errors="replace")
                    pf = parser.parse(str(path.relative_to(source_dir)), source)
                    parsed_files.append(pf)
                except Exception:
                    pass  # skip unparseable files

            # also attempt config parsing
            try:
                source = path.read_text(errors="replace")
                config_vals = parse_config_file(str(path.relative_to(source_dir)), source)
                if config_vals and parsed_files:
                    parsed_files[-1].config_values.extend(config_vals)
            except Exception:
                pass

            if notifier:
                await notifier({"type": "progress", "current": i + 1, "total": len(paths), "file": str(path)})

        # score entry points
        call_targets = {
            c
            for pf in parsed_files
            for fn in (list(pf.functions) + [m for cls in pf.classes for m in cls.methods])
            for c in fn.calls
        }
        for pf in parsed_files:
            for fn in pf.functions + [m for cls in pf.classes for m in cls.methods]:
                fn.entry_point_score = score_entry_point(fn, Path(pf.file_path).stem, fn.qualified_name in call_targets)

        g = RDFBuilder().build(project_id, parsed_files)
        save_graph(g, project_id, data_dir)

        if notifier:
            await notifier({"type": "done", "triples": len(g)})
