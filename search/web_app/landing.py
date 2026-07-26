"""Markdown-driven public landing page for a TsaKorpus corpus."""

from pathlib import Path
import re

from elasticsearch.exceptions import ConnectionError, NotFoundError
from flask import render_template
from markdown import Markdown
from markupsafe import Markup


ABOUT_FILE = Path(__file__).resolve().parents[2] / "conf" / "about.md"
DEFAULT_ACCENT = "#2f6f68"
GROUP_NAMES = {
    "pos": "Части речи",
    "case": "Падеж",
    "Cases": "Падежи",
    "number": "Число",
    "Number": "Число",
    "gender": "Род",
    "person": "Лицо",
    "tense": "Время",
    "mood": "Наклонение",
    "aspect": "Вид",
    "Aspect": "Вид",
    "animacy": "Одушевлённость",
    "voice": "Залог",
    "Agreement": "Согласование",
    "Negation": "Отрицание",
    "Non-finite": "Нефинитные формы",
    "verb_form": "Глагольные формы",
    "style": "Стилистические пометы",
    "variant": "Варианты формы",
}


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
        "words": int(
            getattr(settings, "corpus_size_total", getattr(settings, "corpus_size", 0))
            or 0
        ),
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


def _language_name(settings, language):
    names = getattr(settings, "landing_language_names", {})
    return names.get(language, language.replace("_", " ").title())


def _group_name(name):
    return GROUP_NAMES.get(name, name)


def _selector_groups(lang_props, selector_name):
    """Keep the same column/header/tag order as the search-page selector."""
    groups = []
    seen = set()
    selector = lang_props.get(selector_name, {})
    fallback_name = "Грамматические признаки" if selector_name == "gramm_selection" else "Глоссы"
    for column in selector.get("columns", []):
        current_group = None
        for item in column:
            if item.get("type") == "header":
                current_group = {
                    "name": _group_name(item.get("value", fallback_name)),
                    "tags": [],
                }
                groups.append(current_group)
                continue
            if item.get("type") not in {"gramm", "gloss", "tag"} or not item.get("value"):
                continue
            tag = item["value"]
            if tag in seen:
                continue
            if current_group is None:
                current_group = {
                    "name": _group_name(item.get("category", fallback_name)),
                    "tags": [],
                }
                groups.append(current_group)
            current_group["tags"].append(
                {"tag": tag, "description": item.get("tooltip", "")}
            )
            seen.add(tag)
    return [group for group in groups if group["tags"]], seen


def _grammar_groups(settings, language, lang_props):
    groups, seen = _selector_groups(lang_props, "gramm_selection")
    fallback_groups = []
    fallback_by_name = {}
    for tag, category in settings.categories.get(language, {}).items():
        if tag in seen:
            continue
        group_name = _group_name(category or "Прочие признаки")
        if group_name not in fallback_by_name:
            fallback_by_name[group_name] = {"name": group_name, "tags": []}
            fallback_groups.append(fallback_by_name[group_name])
        fallback_by_name[group_name]["tags"].append({"tag": tag, "description": ""})
        seen.add(tag)
    return groups + fallback_groups


def _annotation_catalog(settings, annotation_type):
    catalog = []
    for language in settings.languages:
        lang_props = settings.lang_props.get(language, {})
        if annotation_type == "grammar":
            groups = _grammar_groups(settings, language, lang_props)
        else:
            groups, unused_seen = _selector_groups(lang_props, "gloss_selection")
        if groups:
            catalog.append(
                {"language": _language_name(settings, language), "groups": groups}
            )
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
        subtitle=_first(meta, "subtitle", ""),
        search_button=_first(meta, "search-button", "Перейти к поиску"),
        accent=_accent(meta),
        content=body,
        toc=Markup(renderer.toc),
        stats=_statistics(settings, search_client),
        show_stats=_enabled(meta, "show-stats"),
        grammar_catalog=_annotation_catalog(settings, "grammar"),
        gloss_catalog=_annotation_catalog(settings, "gloss"),
        show_grammar=_enabled(meta, "show-grammar"),
    )
