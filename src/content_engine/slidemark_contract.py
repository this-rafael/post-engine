"""Contrato SlideMark v1 espelhado do schema Zod do SlideMark."""
from __future__ import annotations

SLIDEMARK_VERSION = "1.0.0"
CANVAS_SIZE = 1080

OFFICIAL_THEMES = frozenset(
    {
        "rafael-io-executive-dark",
        "diffvision-dark",
        "diffvision-dracula",
        "diffvision-lust",
        "diffvision-one-light",
        "diffvision-min-light",
        "diffvision-papercolor-light",
        "mongodb-dark",
        "mongodb-light",
    }
)
SLIDE_TYPES = frozenset(
    {
        "cover.hero",
        "content.text",
        "content.code",
        "content.image",
        "content.screenshot",
        "content.bullets",
        "content.compare",
        "closing.cta",
    }
)
SLIDE_VARIANTS = frozenset({"alpha", "bravo", "charlie"})
TEXT_ALIGNS = frozenset({"left", "center", "justify"})
EXPORT_FORMATS = frozenset({"png", "zip", "pdf"})
DOCUMENT_LANGUAGES = frozenset({"pt-BR", "en-US"})
MEDIA_FITS = frozenset(
    {"contain", "cover", "crop-center", "wide-banner", "screenshot-frame"}
)
MEDIA_SLIDE_TYPES = frozenset(
    {"cover.hero", "content.image", "content.screenshot", "closing.cta"}
)

# These sets mirror the strict Zod objects in SlideMark. They are shared by the
# sanitizer and documented in the LLM contract below.
ROOT_FIELDS = frozenset(
    {"version", "document", "canvas", "theme", "author", "settings", "export", "slides"}
)
BASE_SLIDE_FIELDS = frozenset(
    {"id", "type", "variant", "title", "subtitle", "textAlign", "decorations"}
)
TYPE_FIELDS = {
    "cover.hero": frozenset({"media", "cta"}),
    "content.text": frozenset({"body", "highlight", "emphasis"}),
    "content.code": frozenset(
        {"description", "language", "code", "highlightLines", "showLineNumbers", "caption"}
    ),
    "content.image": frozenset({"description", "media", "caption"}),
    "content.screenshot": frozenset(
        {"description", "media", "caption", "frame", "annotations"}
    ),
    "content.bullets": frozenset({"bullets", "style"}),
    "content.compare": frozenset({"left", "right", "comparisonStyle"}),
    "closing.cta": frozenset({"body", "text", "cta", "media"}),
}


__all__ = [
    "BASE_SLIDE_FIELDS",
    "CANVAS_SIZE",
    "DOCUMENT_LANGUAGES",
    "EXPORT_FORMATS",
    "MEDIA_FITS",
    "MEDIA_SLIDE_TYPES",
    "OFFICIAL_THEMES",
    "ROOT_FIELDS",
    "SLIDEMARK_VERSION",
    "SLIDE_TYPES",
    "SLIDE_VARIANTS",
    "TEXT_ALIGNS",
    "TYPE_FIELDS",
]
