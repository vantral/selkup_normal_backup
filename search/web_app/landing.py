"""Markdown-driven bilingual public landing page for a TsaKorpus corpus."""

from csv import DictReader
from pathlib import Path
import re

from elasticsearch.exceptions import ConnectionError, NotFoundError
from flask import render_template, request
from markdown import Markdown
from markupsafe import Markup


ROOT = Path(__file__).resolve().parents[2]
ABOUT_FILES = {"ru": ROOT / "conf" / "about.md", "en": ROOT / "conf" / "about.en.md"}
ANNOTATIONS_FILE = ROOT / "conf" / "landing_annotations.csv"
DEFAULT_ACCENT = "#2f6f68"

UI = {
    "ru": {
        "project_name": "Малые языки России",
        "institute": "Проект Института языкознания РАН",
        "collection": "Корпуса ЛИСМЯ",
        "contents": "На этой странице",
        "corpus_contents": "Состав корпуса",
        "texts": "текстов",
        "sentences": "предложений",
        "words": "слов",
        "grammar": "Грамматика",
        "grammar_intro": (
            "Грамматические теги описывают свойства словоформы или анализа целиком: "
            "часть речи, падеж, число, лицо, время и другие характеристики."
        ),
        "glosses": "Глоссы",
        "gloss_intro": (
            "Глоссы относятся к отдельным морфемам внутри разбора. Они кратко "
            "обозначают значение или функцию корня, аффикса или другого элемента."
        ),
        "filter": "Фильтр обозначений",
        "filter_placeholder": "Введите тег или расшифровку",
        "open_explanation": "Нажмите, чтобы открыть пояснение",
        "other_grammar": "Прочие грамматические признаки",
        "other_glosses": "Прочие глоссы",
        "search": "Перейти к поиску",
    },
    "en": {
        "project_name": "Minor Languages of Russia",
        "institute": "A project of the Institute of Linguistics, RAS",
        "collection": "LISMYA corpora",
        "contents": "On this page",
        "corpus_contents": "Corpus contents",
        "texts": "texts",
        "sentences": "sentences",
        "words": "words",
        "grammar": "Grammar",
        "grammar_intro": (
            "Grammar tags describe a word form or an analysis as a whole: part of "
            "speech, case, number, person, tense, and other properties."
        ),
        "glosses": "Glosses",
        "gloss_intro": (
            "Glosses refer to individual morphemes within an analysis. They briefly "
            "identify the meaning or function of a root, affix, or another element."
        ),
        "filter": "Filter labels",
        "filter_placeholder": "Enter a tag or explanation",
        "open_explanation": "Select to read the explanation",
        "other_grammar": "Other grammatical features",
        "other_glosses": "Other glosses",
        "search": "Open search",
    },
}

GROUP_NAMES = {
    "ru": {
        "pos": "Части речи", "case": "Падеж", "Cases": "Падежи",
        "number": "Число", "Number": "Число", "gender": "Род",
        "person": "Лицо", "tense": "Время", "Tense": "Время",
        "mood": "Наклонение", "Mood": "Наклонение", "aspect": "Вид",
        "Aspect": "Вид", "animacy": "Одушевлённость", "voice": "Залог",
        "Agreement": "Согласование", "Negation": "Отрицание",
        "Non-finite": "Нефинитные формы", "verb_form": "Глагольные формы",
        "style": "Стилистические пометы", "variant": "Варианты формы",
        "Valency derivation": "Изменение валентности",
        "Denominal derivation": "Отыменная деривация",
        "Nominal derivation": "Именная деривация",
        "Numerals": "Числительные", "Particles": "Частицы",
        "Possessiveness": "Посессивность", "Other tags": "Прочие пометы",
    },
    "en": {
        "pos": "Parts of speech", "case": "Case", "Cases": "Cases",
        "number": "Number", "Number": "Number", "gender": "Gender",
        "person": "Person", "tense": "Tense", "Tense": "Tense",
        "mood": "Mood", "Mood": "Mood", "aspect": "Aspect",
        "Aspect": "Aspect", "animacy": "Animacy", "voice": "Voice",
        "Agreement": "Agreement", "Negation": "Negation",
        "Non-finite": "Non-finite forms", "verb_form": "Verb forms",
        "style": "Stylistic labels", "variant": "Form variants",
        "Valency derivation": "Valency-changing derivation",
        "Denominal derivation": "Denominal derivation",
        "Nominal derivation": "Nominal derivation",
        "Numerals": "Numerals", "Particles": "Particles",
        "Possessiveness": "Possessiveness", "Other tags": "Other tags",
    },
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


def _annotations():
    rows = {}
    if not ANNOTATIONS_FILE.exists():
        return rows
    with ANNOTATIONS_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in DictReader(source):
            language = (row.get("language") or "*").strip()
            kind = (row.get("kind") or "").strip()
            key = (row.get("key") or "").strip()
            if kind and key:
                rows[(language, kind, key)] = row
    return rows


def _override(rows, language, kind, key):
    return rows.get((language, kind, key)) or rows.get(("*", kind, key)) or {}


def _localized(row, field, locale):
    return (row.get(f"{field}_{locale}") or "").strip()


def _language_name(settings, rows, language, locale):
    override = _localized(_override(rows, language, "language", language), "title", locale)
    if override:
        return override
    setting_name = "landing_language_names_en" if locale == "en" else "landing_language_names"
    names = getattr(settings, setting_name, {})
    return names.get(language, language.replace("_", " ").title())


def _group_name(rows, language, name, locale):
    override = _localized(_override(rows, language, "group", name), "title", locale)
    return override or GROUP_NAMES[locale].get(name, name.replace("_", " ").title())


def _tag_item(rows, language, tag, tooltip, locale, ui):
    override = _override(rows, language, "tag", tag)
    title = _localized(override, "title", locale)
    description = _localized(override, "description", locale)
    tooltip = (tooltip or "").strip()
    if not title and tooltip and tooltip.casefold() != tag.casefold():
        title = tooltip
    if not title:
        title = f"{ui['open_explanation']}?"
    if not description:
        description = title
    return {"tag": tag, "title": title, "description": description}


def _selector_groups(lang_props, selector_name, rows, language, locale, ui):
    """Keep the exact column, group and tag order used on the search page."""
    groups = []
    seen = set()
    selector = lang_props.get(selector_name, {})
    fallback = ui["other_grammar"] if selector_name == "gramm_selection" else ui["other_glosses"]
    for column in selector.get("columns", []):
        current_group = None
        for item in column:
            if item.get("type") == "header":
                raw_name = item.get("value") or fallback
                current_group = {
                    "name": _group_name(rows, language, raw_name, locale),
                    "raw_name": raw_name,
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
                raw_name = item.get("category") or fallback
                current_group = {
                    "name": _group_name(rows, language, raw_name, locale),
                    "raw_name": raw_name,
                    "tags": [],
                }
                groups.append(current_group)
            current_group["tags"].append(
                _tag_item(rows, language, tag, item.get("tooltip", ""), locale, ui)
            )
            seen.add(tag)
    return [group for group in groups if group["tags"]], seen


def _grammar_groups(settings, language, lang_props, rows, locale, ui):
    groups, seen = _selector_groups(
        lang_props, "gramm_selection", rows, language, locale, ui
    )
    fallback_groups = []
    fallback_by_name = {}
    for tag, category in settings.categories.get(language, {}).items():
        if tag in seen:
            continue
        raw_name = category or ui["other_grammar"]
        group_name = _group_name(rows, language, raw_name, locale)
        if group_name not in fallback_by_name:
            fallback_by_name[group_name] = {
                "name": group_name, "raw_name": raw_name, "tags": []
            }
            fallback_groups.append(fallback_by_name[group_name])
        fallback_by_name[group_name]["tags"].append(
            _tag_item(rows, language, tag, "", locale, ui)
        )
        seen.add(tag)
    return groups + fallback_groups


def _annotation_catalog(settings, annotation_type, rows, locale, ui):
    catalog = []
    for language in settings.languages:
        lang_props = settings.lang_props.get(language, {})
        if annotation_type == "grammar":
            groups = _grammar_groups(
                settings, language, lang_props, rows, locale, ui
            )
        else:
            groups, _ = _selector_groups(
                lang_props, "gloss_selection", rows, language, locale, ui
            )
        if groups:
            catalog.append(
                {
                    "language": _language_name(settings, rows, language, locale),
                    "language_code": language,
                    "groups": groups,
                }
            )
    return catalog


def render_landing_page(settings, search_client):
    locale = request.args.get("lang", "ru").lower()
    if locale not in UI:
        locale = "ru"
    ui = UI[locale]
    about_file = ABOUT_FILES[locale]
    if not about_file.exists():
        about_file = ABOUT_FILES["ru"]
    source = about_file.read_text(encoding="utf-8") if about_file.exists() else ""
    renderer = Markdown(extensions=["extra", "meta", "sane_lists", "toc"])
    body = Markup(renderer.convert(source))
    meta = renderer.Meta
    rows = _annotations()
    title = _first(meta, "title", settings.corpus_name.replace("_", " ").title())

    return render_template(
        "landing.html",
        title=title,
        subtitle=_first(meta, "subtitle", ""),
        search_button=_first(meta, "search-button", ui["search"]),
        accent=_accent(meta),
        content=body,
        toc=Markup(renderer.toc),
        stats=_statistics(settings, search_client),
        show_stats=_enabled(meta, "show-stats"),
        grammar_catalog=_annotation_catalog(settings, "grammar", rows, locale, ui),
        gloss_catalog=_annotation_catalog(settings, "gloss", rows, locale, ui),
        show_grammar=_enabled(meta, "show-grammar"),
        ui=ui,
        current_lang=locale,
    )
