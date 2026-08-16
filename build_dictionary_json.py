# -*- coding: utf-8 -*-
"""
build_dictionary_json.py

Конвертирует нашу рабочую базу (dictionary_full.json, с ударениями и
флагом needs_review) в лёгкий формат, который читает online-словарь
(dictionary.json):

    [
      {"word": "Борода́", "key": "борода", "def": "БОРОДА, -ы, ...", "review": false},
      ...
    ]

- "word"   — заголовок для показа (первая буква заглавная, ударение —
             это символ U+0301 COMBINING ACUTE ACCENT сразу после гласной,
             браузер сам отрисует её как знак ударения над буквой)
- "key"    — служебный ключ для поиска/сопоставления: нижний регистр, без
             ударений (по нему matчатся клики на слова внутри определений)
- "def"    — полный текст статьи как есть (грамматические формы + толкование + примеры)
- "review" — true, если статья не прошла проверку по словарю ударений/pymorphy3
             и может содержать необнаруженную опечатку OCR

Также индексирует вторые заголовки внутри "слипшихся" статей
(напр. "БОРОНИТЬ ... И БОРОНОВАТЬ") как алиасы на ту же статью,
чтобы поиск "бороновать" тоже находил нужную запись.

Запуск:
    python3 build_dictionary_json.py dictionary_full.json dictionary.json
"""
import json
import sys


def to_display_word(headword_ocr, stressed_form, headword_corrected):
    """Строит красиво читаемое заглавное слово с ударением, если оно есть,
    иначе просто нормальный регистр без ударения (заглавная первая буква)."""
    base = (headword_corrected or headword_ocr).lower()
    if stressed_form:
        display = stressed_form.replace("+", "\u0301")  # комбинируемый акут
        # подстраховка: если исправленная форма не совпадает с ударяемой
        # (не должно происходить, но на всякий случай не теряем слово)
        if display.replace("\u0301", "") != base:
            display = base
    else:
        display = base
    return display[0].upper() + display[1:] if display else display


FRONT_MATTER_MARKERS = ("ISBN", "УДК", "ББК", "Редактор", "составлен")
MAX_DEF_LEN = 1500


def looks_like_front_matter(text):
    return any(marker in text for marker in FRONT_MATTER_MARKERS)


def main(src_path, dst_path):
    with open(src_path, encoding="utf-8") as f:
        entries = json.load(f)

    # первый проход: выбрать по каждому ключу лучшую (самую полную) версию,
    # если слово по ошибке распознано как отдельная статья несколько раз
    best_by_key = {}
    for e in entries:
        headword_ocr = e["headword_ocr"]
        corrected = e.get("headword_corrected")
        primary_plain = (corrected or headword_ocr).lower()
        prev = best_by_key.get(primary_plain)
        if prev is None or len(e["full_text_ocr"]) > len(prev["full_text_ocr"]):
            best_by_key[primary_plain] = e

    out = []
    key_seen = set()
    alias_count = 0

    for primary_plain, e in best_by_key.items():
        headword_ocr = e["headword_ocr"]
        corrected = e.get("headword_corrected")
        stressed = e.get("stressed_form")
        review = bool(e.get("needs_review"))
        def_text = e["full_text_ocr"]

        # выбросить обрывки предисловия/выходных данных, случайно затесавшиеся
        # в статьи парсером (напр. под словом "СЛОВАРЬ" из титульного листа)
        if looks_like_front_matter(def_text) and len(def_text) > 800:
            continue

        # аномально длинные статьи почти всегда означают, что парсер по ошибке
        # слепил вместе несколько соседних статей - обрезаем и помечаем на проверку
        if len(def_text) > MAX_DEF_LEN:
            def_text = def_text[:MAX_DEF_LEN].rsplit(" ", 1)[0] + "… [текст обрезан, требует проверки]"
            review = True

        key_seen.add(primary_plain)
        word_display = to_display_word(headword_ocr, stressed, corrected)

        record = {
            "word": word_display,
            "key": primary_plain,
            "def": def_text,
            "review": review,
        }
        out.append(record)

        # доп. заголовки в той же статье (напр. "БОРОНИТЬ, ... И БОРОНОВАТЬ")
        # индексируем как алиасы на тот же текст, если они реально отдельные слова
        variants = e.get("headword_variants_ocr") or []
        for v in variants[1:]:
            v_plain = v.strip().lower()
            # отбрасываем мусорные "варианты" (не отдельное слово, обрывок и т.п.)
            if not v_plain.isalpha() or v_plain in key_seen or len(v_plain) < 3:
                continue
            key_seen.add(v_plain)
            out.append({
                "word": v_plain[0].upper() + v_plain[1:],
                "key": v_plain,
                "def": def_text,
                "review": review,
            })
            alias_count += 1

    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Статей на входе: {len(entries)}")
    print(f"Записей на выходе (с алиасами): {len(out)}")
    print(f"  из них алиасов: {alias_count}")
    print(f"Сохранено в {dst_path}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "dictionary_full.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "dictionary.json"
    main(src, dst)
