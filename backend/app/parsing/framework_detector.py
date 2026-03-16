from typing import Optional


def detect_framework_role(node_name: str, annotations: list[str], imports: list[str]) -> Optional[str]:
    # Spring
    if any(a in annotations for a in ["GetMapping", "PostMapping", "PutMapping", "DeleteMapping"]):
        return "rest_endpoint"
    if "RestController" in annotations:
        return "rest_controller"
    if "Service" in annotations:
        return "service"
    if "Repository" in annotations:
        return "repository"
    # Express / Gin / FastAPI patterns via import heuristics
    if any("express" in i for i in imports) and node_name in ("app", "router"):
        return "express_router"
    if any("gin" in i for i in imports) and node_name in ("r", "router", "engine"):
        return "gin_router"
    if any("fastapi" in i for i in imports):
        return "fastapi_route"
    # Test frameworks
    if any(a in annotations for a in ["Test", "test", "it", "describe"]):
        return "test"
    # ORM
    if "Entity" in annotations or any("ActiveRecord" in i for i in imports):
        return "entity"
    return None
