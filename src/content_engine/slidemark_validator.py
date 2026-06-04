"""Normalizacao e validacao estrita do contrato SlideMark JSON v1.

O contrato espelha ``src/core/schema/slidemark.schema.ts`` do SlideMark. A
normalizacao existe apenas para recuperar formatos legados sem inventar dados;
o documento resultante sempre passa pela validacao estrita antes da exportacao.
"""
from __future__ import annotations

import re
from typing import Any

from .slidemark_contract import (
    BASE_SLIDE_FIELDS,
    CANVAS_SIZE,
    DOCUMENT_LANGUAGES,
    EXPORT_FORMATS,
    MEDIA_FITS,
    MEDIA_SLIDE_TYPES,
    OFFICIAL_THEMES,
    ROOT_FIELDS,
    SLIDEMARK_VERSION,
    SLIDE_TYPES,
    SLIDE_VARIANTS,
    TEXT_ALIGNS,
    TYPE_FIELDS,
)

_POSITION_VALUES = {
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
    "left-center",
    "right-center",
    "center",
}
_DECORATION_TYPES = {"accent-symbol", "circle", "arrow"}
_ANNOTATION_TYPES = {"arrow", "circle", "box", "label"}
_BULLET_STYLES = {"default", "checklist", "numbered"}
_COMPARE_STYLES = {"before-after", "right-wrong", "pros-cons"}
_EMPHASIS_STYLES = {"bold", "accent", "muted", "strike"}
_SCREENSHOT_FRAMES = {"browser", "editor", "plain"}
_UPLOADED_IMAGE_RE = re.compile(
    r"^@uploaded[A-Za-z0-9-]*\.(?:png|jpe?g|gif|webp|svg|avif)$", re.IGNORECASE
)
_HANDLE_RE = re.compile(r"^@[A-Za-z0-9_.-]{2,}$")


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _optional_text(value: object) -> str | None:
    text = _text(value)
    return text or None


def _supported_media_source(value: object) -> bool:
    source = _text(value)
    return bool(
        source
        and (
            source.lower() == "@placeholderimage"
            or source.startswith(("http://", "https://", "data:image/", "/", "./", "../"))
            or bool(_UPLOADED_IMAGE_RE.fullmatch(source))
        )
    )


def _clean_image(value: object, *, media: bool = False) -> dict[str, Any] | None:
    raw = {"src": value} if isinstance(value, str) else _dict(value)
    source = _optional_text(raw.get("src"))
    if not source:
        return None
    cleaned: dict[str, Any] = {"src": source}
    alt = _optional_text(raw.get("alt"))
    if alt:
        cleaned["alt"] = alt
    if media:
        cleaned["type"] = "image"
        fit = raw.get("fit")
        cleaned["fit"] = fit if fit in MEDIA_FITS else "contain"
    return cleaned


def _clean_decorations(value: object) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for raw in _list(value):
        item = _dict(raw)
        decoration: dict[str, Any] = {}
        if isinstance(item.get("type"), str):
            decoration["type"] = item["type"]
        if item.get("position") in _POSITION_VALUES:
            decoration["position"] = item["position"]
        for key in ("x", "y", "width", "height", "rotation"):
            if _is_number(item.get(key)):
                decoration[key] = item[key]
        for key in ("label", "symbol"):
            text = _optional_text(item.get(key))
            if text:
                decoration[key] = text
        cleaned.append(decoration)
    return cleaned


def _clean_annotations(value: object) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for raw in _list(value):
        item = _dict(raw)
        annotation: dict[str, Any] = {}
        if isinstance(item.get("type"), str):
            annotation["type"] = item["type"]
        for key in ("x", "y", "width", "height"):
            if _is_number(item.get(key)):
                annotation[key] = item[key]
        for key in ("label", "text"):
            text = _optional_text(item.get(key))
            if text:
                annotation[key] = text
        cleaned.append(annotation)
    return cleaned


def _clean_bullets(value: object) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for raw in _list(value):
        item = {"text": raw} if isinstance(raw, str) else _dict(raw)
        bullet: dict[str, Any] = {}
        text = _optional_text(item.get("text"))
        if text:
            bullet["text"] = text
        for key in ("description", "icon"):
            optional = _optional_text(item.get(key))
            if optional:
                bullet[key] = optional
        cleaned.append(bullet)
    return cleaned


def _clean_compare_column(value: object) -> dict[str, Any]:
    item = _dict(value)
    column: dict[str, Any] = {}
    for key in ("title", "label"):
        text = _optional_text(item.get(key))
        if text:
            column[key] = text
    items = [_optional_text(entry) for entry in _list(item.get("items"))]
    column["items"] = [entry for entry in items if entry]
    return column


def _clean_suggestion(value: object) -> dict[str, str] | None:
    item = _dict(value)
    # Older generation payloads use ``slide``/``sugestao``. Accept them at
    # the export boundary, then keep the canonical SlideMark media shape.
    description = _optional_text(
        item.get("descricao") or item.get("sugestao") or item.get("description")
    )
    if not description:
        return None
    mode = "link" if _text(item.get("modo")).lower() == "link" else "descricao"
    url = _optional_text(item.get("url"))
    return {"descricao": description, "modo": mode, **({"url": url} if url else {})}


def _index_suggestions(
    suggestions: list[dict[str, Any]] | None,
) -> tuple[dict[str, dict[str, str]], dict[int, dict[str, str]]]:
    by_id: dict[str, dict[str, str]] = {}
    by_number: dict[int, dict[str, str]] = {}
    for raw in suggestions or []:
        if not isinstance(raw, dict):
            continue
        suggestion = _clean_suggestion(raw.get("sugestaoImagem", raw))
        if suggestion is None:
            continue
        slide_id = _optional_text(raw.get("slideId") or raw.get("slide_id") or raw.get("id"))
        if slide_id:
            by_id[slide_id] = suggestion
        number = raw.get("numero") or raw.get("ordem") or raw.get("slide")
        if isinstance(number, int) and not isinstance(number, bool) and number > 0:
            by_number[number] = suggestion
    return by_id, by_number


def _apply_suggestion_media(
    slide: dict[str, Any],
    suggestion: dict[str, str] | None,
) -> None:
    if suggestion is None or slide.get("type") not in MEDIA_SLIDE_TYPES:
        return
    url = suggestion.get("url") if suggestion.get("modo") == "link" else None
    source = url if _supported_media_source(url) else "@placeholderImage"
    current = _dict(slide.get("media"))
    media = {
        "type": "image",
        "src": source,
        "alt": suggestion["descricao"],
        "fit": current.get("fit") if current.get("fit") in MEDIA_FITS else "contain",
    }
    slide["media"] = media
    if slide["type"] == "cover.hero" and slide.get("variant") == "alpha":
        slide["variant"] = "bravo"
    if slide["type"] == "closing.cta" and slide.get("variant") != "bravo":
        slide["variant"] = "bravo"


def _clean_slide(
    raw: object,
    index: int,
    by_id: dict[str, dict[str, str]],
    by_number: dict[int, dict[str, str]],
) -> dict[str, Any]:
    item = _dict(raw)
    slide_type = item.get("type")
    allowed = BASE_SLIDE_FIELDS | TYPE_FIELDS.get(slide_type, frozenset())
    slide: dict[str, Any] = {}
    for key in ("id", "title", "subtitle"):
        text = _optional_text(item.get(key))
        if text:
            slide[key] = text
    if isinstance(slide_type, str):
        slide["type"] = slide_type
    variant = item.get("variant")
    slide["variant"] = variant if variant in SLIDE_VARIANTS else "alpha"
    if item.get("textAlign") in TEXT_ALIGNS:
        slide["textAlign"] = item["textAlign"]
    slide["decorations"] = _clean_decorations(item.get("decorations"))

    if slide_type == "cover.hero":
        cta = _optional_text(item.get("cta"))
        if cta:
            slide["cta"] = cta
    elif slide_type == "content.text":
        body = item.get("body")
        if isinstance(body, str):
            body = [body]
        slide["body"] = [text for entry in _list(body) if (text := _optional_text(entry))]
        highlight = item.get("highlight")
        if isinstance(highlight, str):
            highlight = {"text": highlight}
        highlight_item = _dict(highlight)
        highlight_text = _optional_text(highlight_item.get("text"))
        if highlight_text:
            cleaned_highlight: dict[str, Any] = {"text": highlight_text}
            label = _optional_text(highlight_item.get("label"))
            if label:
                cleaned_highlight["label"] = label
            slide["highlight"] = cleaned_highlight
        emphasis: list[dict[str, str]] = []
        for raw_emphasis in _list(item.get("emphasis")):
            emphasis_item = _dict(raw_emphasis)
            text = _optional_text(emphasis_item.get("text"))
            style = emphasis_item.get("style")
            if text and style in _EMPHASIS_STYLES:
                emphasis.append({"text": text, "style": style})
        slide["emphasis"] = emphasis
    elif slide_type == "content.code":
        for key in ("description", "language", "code", "caption"):
            text = _optional_text(item.get(key))
            if text:
                slide[key] = text
        slide["highlightLines"] = [
            line for line in _list(item.get("highlightLines")) if _is_positive_int(line)
        ]
        slide["showLineNumbers"] = bool(item.get("showLineNumbers"))
    elif slide_type in {"content.image", "content.screenshot"}:
        for key in ("description", "caption"):
            text = _optional_text(item.get(key))
            if text:
                slide[key] = text
        media = _clean_image(item.get("media"), media=True)
        if media:
            slide["media"] = media
        if slide_type == "content.screenshot":
            frame = item.get("frame")
            slide["frame"] = frame if frame in _SCREENSHOT_FRAMES else "browser"
            slide["annotations"] = _clean_annotations(item.get("annotations"))
    elif slide_type == "content.bullets":
        slide["bullets"] = _clean_bullets(item.get("bullets"))
        style = item.get("style")
        slide["style"] = style if style in _BULLET_STYLES else "default"
    elif slide_type == "content.compare":
        slide["left"] = _clean_compare_column(item.get("left"))
        slide["right"] = _clean_compare_column(item.get("right"))
        style = item.get("comparisonStyle")
        slide["comparisonStyle"] = style if style in _COMPARE_STYLES else "before-after"
    elif slide_type == "closing.cta":
        body = item.get("body")
        if isinstance(body, str):
            body = [body]
        slide["body"] = [text for entry in _list(body) if (text := _optional_text(entry))]
        for key in ("text", "cta"):
            text = _optional_text(item.get(key))
            if text:
                slide[key] = text

    if slide_type in MEDIA_SLIDE_TYPES and "media" not in slide:
        media = _clean_image(item.get("media"), media=True)
        if media and media.get("src", "").lower() != "@placeholderimage":
            slide["media"] = media

    suggestion = by_id.get(str(slide.get("id", ""))) or by_number.get(index)
    if suggestion is None:
        media = _dict(slide.get("media"))
        if _text(media.get("src")).lower() == "@placeholderimage":
            slide.pop("media", None)
    _apply_suggestion_media(slide, suggestion)
    # ``allowed`` is intentionally computed with the discriminator so a new
    # field cannot leak from a legacy slide into another template.
    return {key: value for key, value in slide.items() if key in allowed}


def normalize_slidemark_document(
    document: object,
    *,
    image_suggestions: list[dict[str, Any]] | None = None,
) -> object:
    """Return a canonical document after lossless or safe legacy cleanup."""
    if not isinstance(document, dict):
        return document
    by_id, by_number = _index_suggestions(image_suggestions)
    normalized: dict[str, Any] = {}
    version = _optional_text(document.get("version"))
    if version:
        normalized["version"] = version
    metadata = _dict(document.get("document"))
    normalized["document"] = {
        key: text
        for key in ("title", "description", "language")
        if (text := _optional_text(metadata.get(key)))
    }
    canvas = _dict(document.get("canvas"))
    normalized["canvas"] = {
        key: canvas[key] for key in ("width", "height") if _is_number(canvas.get(key))
    }
    theme = document.get("theme")
    if isinstance(theme, dict):
        theme = theme.get("id")
    theme_text = _optional_text(theme)
    if theme_text:
        normalized["theme"] = theme_text
    author = _dict(document.get("author"))
    normalized["author"] = {
        key: text
        for key in ("name", "handle")
        if (text := _optional_text(author.get(key)))
    }
    if "avatar" in author:
        avatar = _clean_image(author.get("avatar"))
        normalized["author"]["avatar"] = avatar if avatar else None

    settings = _dict(document.get("settings"))
    normalized["settings"] = {
        "showAuthor": bool(settings.get("showAuthor", True)),
        "showPageNumber": bool(settings.get("showPageNumber", True)),
        "showSwipeHint": bool(settings.get("showSwipeHint", True)),
        "swipeHintText": _optional_text(settings.get("swipeHintText"))
        or "Desliza para esquerda",
    }
    export = _dict(document.get("export"))
    normalized["export"] = {}
    file_name = _optional_text(export.get("fileName"))
    if file_name:
        normalized["export"]["fileName"] = file_name
    formats = [entry for entry in _list(export.get("formats")) if entry in EXPORT_FORMATS]
    normalized["export"]["formats"] = list(dict.fromkeys(formats))
    pdf = _dict(export.get("pdf"))
    normalized["export"]["pdf"] = {
        "pageMode": pdf.get("pageMode"),
        "source": pdf.get("source"),
    }
    raw_slides = document.get("slides")
    normalized["slides"] = [
        _clean_slide(raw, index, by_id, by_number)
        for index, raw in enumerate(_list(raw_slides), start=1)
    ]
    return {key: value for key, value in normalized.items() if key in ROOT_FIELDS}


def _expect_exact_keys(errors: list[str], value: object, allowed: set[str] | frozenset[str], path: str) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} deve ser objeto")
        return
    extra = sorted(set(value) - set(allowed))
    for key in extra:
        errors.append(f"{path}.{key} nao e permitido")


def _require_text(errors: list[str], value: object, path: str) -> None:
    if not _text(value):
        errors.append(f"{path} deve ser texto nao vazio")


def _optional_text_error(errors: list[str], value: object, path: str) -> None:
    if value is not None and not _text(value):
        errors.append(f"{path} deve ser texto nao vazio quando informado")


def _validate_image(errors: list[str], value: object, path: str, *, media: bool = False) -> None:
    allowed = {"src", "alt"} | ({"type", "fit"} if media else set())
    _expect_exact_keys(errors, value, allowed, path)
    if not isinstance(value, dict):
        return
    _require_text(errors, value.get("src"), f"{path}.src")
    if _text(value.get("src")) and not _supported_media_source(value.get("src")):
        errors.append(f"{path}.src possui fonte nao suportada")
    _optional_text_error(errors, value.get("alt"), f"{path}.alt")
    if media:
        if "type" in value and value.get("type") != "image":
            errors.append(f"{path}.type deve ser image")
        if "fit" in value and value.get("fit") not in MEDIA_FITS:
            errors.append(f"{path}.fit e invalido")


def _validate_decorations(errors: list[str], value: object, path: str) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{path} deve ser lista")
        return
    allowed = {"type", "position", "x", "y", "width", "height", "label", "symbol", "rotation"}
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        _expect_exact_keys(errors, raw, allowed, item_path)
        item = _dict(raw)
        if item.get("type") not in _DECORATION_TYPES:
            errors.append(f"{item_path}.type e invalido")
        if "position" in item and item.get("position") not in _POSITION_VALUES:
            errors.append(f"{item_path}.position e invalida")
        for key in ("x", "y"):
            if key in item and (not _is_number(item[key]) or not 0 <= item[key] <= CANVAS_SIZE):
                errors.append(f"{item_path}.{key} deve estar entre 0 e {CANVAS_SIZE}")
        for key in ("width", "height"):
            if key in item and (not _is_number(item[key]) or not 0 < item[key] <= CANVAS_SIZE):
                errors.append(f"{item_path}.{key} deve ser positivo ate {CANVAS_SIZE}")
        if "rotation" in item and (not _is_number(item["rotation"]) or not -360 <= item["rotation"] <= 360):
            errors.append(f"{item_path}.rotation deve estar entre -360 e 360")
        for key in ("label", "symbol"):
            _optional_text_error(errors, item.get(key), f"{item_path}.{key}")


def _validate_base_slide(errors: list[str], slide: dict[str, Any], index: int) -> None:
    path = f"slides[{index}]"
    _require_text(errors, slide.get("id"), f"{path}.id")
    _require_text(errors, slide.get("title"), f"{path}.title")
    _optional_text_error(errors, slide.get("subtitle"), f"{path}.subtitle")
    if "variant" in slide and slide.get("variant") not in SLIDE_VARIANTS:
        errors.append(f"{path}.variant e invalida")
    if "textAlign" in slide and slide.get("textAlign") not in TEXT_ALIGNS:
        errors.append(f"{path}.textAlign e invalido")
    _validate_decorations(errors, slide.get("decorations"), f"{path}.decorations")


def _validate_annotations(errors: list[str], value: object, path: str) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{path} deve ser lista")
        return
    allowed = {"type", "x", "y", "width", "height", "label", "text"}
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        _expect_exact_keys(errors, raw, allowed, item_path)
        item = _dict(raw)
        if item.get("type") not in _ANNOTATION_TYPES:
            errors.append(f"{item_path}.type e invalido")
        for key in ("x", "y"):
            if not _is_number(item.get(key)) or not 0 <= item[key] <= CANVAS_SIZE:
                errors.append(f"{item_path}.{key} deve estar entre 0 e {CANVAS_SIZE}")
        for key in ("width", "height"):
            if key in item and (not _is_number(item[key]) or not 0 < item[key] <= CANVAS_SIZE):
                errors.append(f"{item_path}.{key} deve ser positivo ate {CANVAS_SIZE}")
        for key in ("label", "text"):
            _optional_text_error(errors, item.get(key), f"{item_path}.{key}")


def _validate_slide(errors: list[str], raw: object, index: int) -> None:
    path = f"slides[{index}]"
    if not isinstance(raw, dict):
        errors.append(f"{path} deve ser objeto")
        return
    slide_type = raw.get("type")
    if slide_type not in SLIDE_TYPES:
        errors.append(f"{path}.type e invalido")
        return
    _expect_exact_keys(errors, raw, BASE_SLIDE_FIELDS | TYPE_FIELDS[slide_type], path)
    _validate_base_slide(errors, raw, index)

    if slide_type == "cover.hero":
        _optional_text_error(errors, raw.get("cta"), f"{path}.cta")
        if "media" in raw:
            _validate_image(errors, raw["media"], f"{path}.media", media=True)
    elif slide_type == "content.text":
        body = raw.get("body")
        if not isinstance(body, list) or not body:
            errors.append(f"{path}.body deve conter ao menos um paragrafo")
        else:
            for body_index, paragraph in enumerate(body):
                _require_text(errors, paragraph, f"{path}.body[{body_index}]")
        if "highlight" in raw:
            _expect_exact_keys(errors, raw["highlight"], {"text", "label"}, f"{path}.highlight")
            highlight = _dict(raw["highlight"])
            _require_text(errors, highlight.get("text"), f"{path}.highlight.text")
            _optional_text_error(errors, highlight.get("label"), f"{path}.highlight.label")
        emphasis = raw.get("emphasis")
        if emphasis is not None and not isinstance(emphasis, list):
            errors.append(f"{path}.emphasis deve ser lista")
        for emphasis_index, entry in enumerate(_list(emphasis)):
            entry_path = f"{path}.emphasis[{emphasis_index}]"
            _expect_exact_keys(errors, entry, {"text", "style"}, entry_path)
            item = _dict(entry)
            _require_text(errors, item.get("text"), f"{entry_path}.text")
            if item.get("style") not in _EMPHASIS_STYLES:
                errors.append(f"{entry_path}.style e invalido")
    elif slide_type == "content.code":
        for key in ("language", "code"):
            _require_text(errors, raw.get(key), f"{path}.{key}")
        for key in ("description", "caption"):
            _optional_text_error(errors, raw.get(key), f"{path}.{key}")
        lines = raw.get("highlightLines")
        if lines is not None and not isinstance(lines, list):
            errors.append(f"{path}.highlightLines deve ser lista")
        for line_index, line in enumerate(_list(lines)):
            if not _is_positive_int(line):
                errors.append(f"{path}.highlightLines[{line_index}] deve ser inteiro positivo")
        if "showLineNumbers" in raw and not isinstance(raw["showLineNumbers"], bool):
            errors.append(f"{path}.showLineNumbers deve ser booleano")
    elif slide_type in {"content.image", "content.screenshot"}:
        if "media" not in raw:
            errors.append(f"{path}.media e obrigatorio")
        else:
            _validate_image(errors, raw["media"], f"{path}.media", media=True)
        for key in ("description", "caption"):
            _optional_text_error(errors, raw.get(key), f"{path}.{key}")
        if slide_type == "content.screenshot":
            if "frame" in raw and raw.get("frame") not in _SCREENSHOT_FRAMES:
                errors.append(f"{path}.frame e invalido")
            _validate_annotations(errors, raw.get("annotations"), f"{path}.annotations")
    elif slide_type == "content.bullets":
        bullets = raw.get("bullets")
        if not isinstance(bullets, list) or not bullets:
            errors.append(f"{path}.bullets deve conter ao menos um item")
        for bullet_index, bullet in enumerate(_list(bullets)):
            bullet_path = f"{path}.bullets[{bullet_index}]"
            _expect_exact_keys(errors, bullet, {"text", "description", "icon"}, bullet_path)
            item = _dict(bullet)
            _require_text(errors, item.get("text"), f"{bullet_path}.text")
            _optional_text_error(errors, item.get("description"), f"{bullet_path}.description")
            _optional_text_error(errors, item.get("icon"), f"{bullet_path}.icon")
        if "style" in raw and raw.get("style") not in _BULLET_STYLES:
            errors.append(f"{path}.style e invalido")
    elif slide_type == "content.compare":
        for side in ("left", "right"):
            side_path = f"{path}.{side}"
            column = raw.get(side)
            _expect_exact_keys(errors, column, {"title", "label", "items"}, side_path)
            item = _dict(column)
            _optional_text_error(errors, item.get("title"), f"{side_path}.title")
            _optional_text_error(errors, item.get("label"), f"{side_path}.label")
            if not _text(item.get("title")) and not _text(item.get("label")):
                errors.append(f"{side_path} precisa de title ou label")
            values = item.get("items")
            if not isinstance(values, list) or not values:
                errors.append(f"{side_path}.items deve conter ao menos um item")
            for item_index, value in enumerate(_list(values)):
                _require_text(errors, value, f"{side_path}.items[{item_index}]")
        if "comparisonStyle" in raw and raw.get("comparisonStyle") not in _COMPARE_STYLES:
            errors.append(f"{path}.comparisonStyle e invalido")
    elif slide_type == "closing.cta":
        _require_text(errors, raw.get("cta"), f"{path}.cta")
        body = raw.get("body")
        if body is not None and not isinstance(body, list):
            errors.append(f"{path}.body deve ser lista")
        for body_index, paragraph in enumerate(_list(body)):
            _require_text(errors, paragraph, f"{path}.body[{body_index}]")
        _optional_text_error(errors, raw.get("text"), f"{path}.text")
        if "media" in raw:
            _validate_image(errors, raw["media"], f"{path}.media", media=True)


def validate_slidemark_document(document: object) -> list[str]:
    """Return validation errors matching the current strict SlideMark schema."""
    errors: list[str] = []
    _expect_exact_keys(errors, document, ROOT_FIELDS, "documento")
    if not isinstance(document, dict):
        return errors
    if document.get("version") != SLIDEMARK_VERSION:
        errors.append(f'version deve ser "{SLIDEMARK_VERSION}"')

    metadata = document.get("document")
    _expect_exact_keys(errors, metadata, {"title", "description", "language"}, "document")
    metadata_dict = _dict(metadata)
    _require_text(errors, metadata_dict.get("title"), "document.title")
    _require_text(errors, metadata_dict.get("description"), "document.description")
    if metadata_dict.get("language") not in DOCUMENT_LANGUAGES:
        errors.append("document.language e invalido")

    canvas = document.get("canvas")
    _expect_exact_keys(errors, canvas, {"width", "height"}, "canvas")
    canvas_dict = _dict(canvas)
    if canvas_dict.get("width") != CANVAS_SIZE:
        errors.append(f"canvas.width deve ser {CANVAS_SIZE}")
    if canvas_dict.get("height") != CANVAS_SIZE:
        errors.append(f"canvas.height deve ser {CANVAS_SIZE}")

    theme = document.get("theme")
    if isinstance(theme, dict):
        _expect_exact_keys(errors, theme, {"id"}, "theme")
        theme = theme.get("id")
    if theme not in OFFICIAL_THEMES:
        errors.append("theme deve ser um tema oficial")

    author = document.get("author")
    _expect_exact_keys(errors, author, {"name", "handle", "avatar"}, "author")
    author_dict = _dict(author)
    _require_text(errors, author_dict.get("name"), "author.name")
    handle = _text(author_dict.get("handle"))
    if not _HANDLE_RE.fullmatch(handle):
        errors.append("author.handle deve iniciar com @ e ter ao menos dois caracteres")
    if "avatar" in author_dict and author_dict["avatar"] is not None:
        _validate_image(errors, author_dict["avatar"], "author.avatar")

    if "settings" in document:
        settings = document["settings"]
        _expect_exact_keys(
            errors,
            settings,
            {"showAuthor", "showPageNumber", "showSwipeHint", "swipeHintText"},
            "settings",
        )
        settings_dict = _dict(settings)
        for key in ("showAuthor", "showPageNumber", "showSwipeHint"):
            if key in settings_dict and not isinstance(settings_dict[key], bool):
                errors.append(f"settings.{key} deve ser booleano")
        if "swipeHintText" in settings_dict:
            _require_text(errors, settings_dict["swipeHintText"], "settings.swipeHintText")

    export = document.get("export")
    _expect_exact_keys(errors, export, {"fileName", "formats", "pdf"}, "export")
    export_dict = _dict(export)
    _require_text(errors, export_dict.get("fileName"), "export.fileName")
    formats = export_dict.get("formats")
    if not isinstance(formats, list) or not formats:
        errors.append("export.formats deve conter ao menos um formato")
    else:
        if any(format_name not in EXPORT_FORMATS for format_name in formats):
            errors.append("export.formats possui formato invalido")
        if len(set(formats)) != len(formats):
            errors.append("export.formats nao deve conter duplicados")
    pdf = export_dict.get("pdf")
    _expect_exact_keys(errors, pdf, {"pageMode", "source"}, "export.pdf")
    pdf_dict = _dict(pdf)
    if pdf_dict.get("pageMode") != "square":
        errors.append("export.pdf.pageMode deve ser square")
    if pdf_dict.get("source") != "rendered-images":
        errors.append("export.pdf.source deve ser rendered-images")

    slides = document.get("slides")
    if not isinstance(slides, list) or not slides:
        errors.append("slides deve conter ao menos um slide")
        return errors
    for index, slide in enumerate(slides):
        _validate_slide(errors, slide, index)
    return errors


def validate_slidemark_export_document(document: object) -> list[str]:
    """Validate the schema plus the product's first/last slide convention."""
    errors = validate_slidemark_document(document)
    if not isinstance(document, dict) or not isinstance(document.get("slides"), list):
        return errors
    slides = document["slides"]
    if slides:
        first = _dict(slides[0])
        last = _dict(slides[-1])
        if first.get("type") != "cover.hero":
            errors.append("primeiro slide deve ser cover.hero")
        if last.get("type") != "closing.cta":
            errors.append("ultimo slide deve ser closing.cta")
    return errors


def is_valid_slidemark_document(document: object) -> bool:
    return not validate_slidemark_document(document)


__all__ = [
    "CANVAS_SIZE",
    "OFFICIAL_THEMES",
    "SLIDE_TYPES",
    "SLIDE_VARIANTS",
    "SLIDEMARK_VERSION",
    "is_valid_slidemark_document",
    "normalize_slidemark_document",
    "validate_slidemark_document",
    "validate_slidemark_export_document",
]
