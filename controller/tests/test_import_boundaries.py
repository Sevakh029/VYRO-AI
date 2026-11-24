import ast
from pathlib import Path

FORBIDDEN_IMPORT_ROOTS = {
    "mqtt",
    "paho",
    "fastapi",
    "traci",
    "sumolib",
    "sumo",
    "sim",
    "simulation",
    "io",
    "os",
    "pathlib",
    "shutil",
    "tempfile",
    "vyro_backend",
}


def test_controller_imports_do_not_depend_on_transport_or_simulator_modules() -> None:
    controller_source = Path(__file__).parents[1] / "src"
    for source_file in controller_source.rglob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "open"
            ):
                raise AssertionError(f"{source_file}: controller must not perform file I/O")
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots = {node.module.split(".", 1)[0]}
            else:
                continue
            forbidden = roots & FORBIDDEN_IMPORT_ROOTS
            assert not forbidden, f"{source_file}: forbidden imports {sorted(forbidden)}"
