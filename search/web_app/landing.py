"""Markdown-driven public landing page for a TsaKorpus corpus."""

from pathlib import Path
import re

from elasticsearch.exceptions import ConnectionError, NotFoundError
from flask import render_template
from markdown import Markdown
from markupsafe import Markup


ABOUT_FILE = Path(__file__).resolve().parents[2] / "conf" / "about.md"
DEFAULT_ACCENT = "#2f6f68"


def _first(meta, key, default=""):
    value = meta.get(key, [])
    return value[0] if value else default


def _enabled(meta, key, default=True):
    value = _first(meta, key, "")
    if not value:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _accent(meta):
    value = _first(meta, "accent", DEFAULT_ACCENT).strip()
    return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else DEFAULT_ACCENT


def _statistics(settings, search_client):
    stats = {
        "documents": 0,
        "sentences": 0,
        "words": int(settings.corpus_size_total or 0),
        "languages": len(settings.languages),
    }
    try:
        stats["documents"] = search_client.es.count(
            index=search_client.name + ".docs"
        )["count"]
        stats["sentences"] = search_client.es.count(
            index=search_client.name + ".sentences*"
        )["count"]
    except (ConnectionError, NotFoundError):
        pass
    return stats


def _selector_entries(lang_props):
    entries = {}
    for selector_name in ("gramm_selection", "gloss_selection"):
        selector = lang_props.get(selector_name, {})
        for column in selector.get("columns", []):
            current_group = "grammar" if selector_name == "gramm_selection" else "glosses"
            for item in column:
                if item.get("type") == "header" and item.get("value"):
                    current_group = item["value"]
                if item.get("type") in {"gramm", "gloss", "tag"} and item.get("value"):
                    entries[item["value"]] = {
                        "category": item.get("category", current_group),
                        "description": item.get("tooltip", ""),
                    }
    return entries


def _grammar_catalog(settings):
    catalog = []
    for language in settings.languages:
        selector_entries = _selector_entries(settings.lang_props.get(language, {}))
        grouped = {}
        for tag, category in settings.categories.get(language, {}).items():
            grouped.setdefault(category or "other", []).append(
                {"tag": tag, "description": selector_entries.get(tag, {}).get("description", "")}
            )
        configured_tags = settings.categories.get(language, {})
        for tag, entry in selector_entries.items():
            if tag not in configured_tags:
                grouped.setdefault(entry["category"] or "other", []).append(
                    {"tag": tag, "description": entry["description"]}
                )
        categories = [
            {"name": name, "tags": sorted(tags, key=lambda item: item["tag"].lower())}
            for name, tags in sorted(grouped.items())
        ]
        if categories:
            catalog.append({"language": language, "categories": categories})
    return catalog


def render_landing_page(settings, search_client):
    source = ABOUT_FILE.read_text(encoding="utf-8") if ABOUT_FILE.exists() else ""
    renderer = Markdown(extensions=["extra", "meta", "sane_lists", "toc"])
    body = Markup(renderer.convert(source))
    meta = renderer.Meta
    title = _first(meta, "title", settings.corpus_name.replace("_", " ").title())

    return render_template(
        "landing.html",
        title=title,
        kicker=_first(meta, "kicker", "Лингвистический корпус"),
        subtitle=_first(meta, "subtitle", ""),
        search_button=_first(meta, "search-button", "Перейти к поиску"),
        accent=_accent(meta),
        content=body,
        toc=Markup(renderer.toc),
        stats=_statistics(settings, search_client),
        show_stats=_enabled(meta, "show-stats"),
        grammar_catalog=_grammar_catalog(settings),
        show_grammar=_enabled(meta, "show-grammar"),
    )
