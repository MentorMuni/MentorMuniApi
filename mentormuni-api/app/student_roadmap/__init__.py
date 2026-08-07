"""Student Week-1 roadmap + OpenAI 90-day placement plan."""

__all__ = ["router"]


def __getattr__(name: str):
    if name == "router":
        from app.student_roadmap.router import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
