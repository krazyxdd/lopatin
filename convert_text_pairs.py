# -*- coding: utf-8 -*-
"""
convert_text_pairs.py

Небольшая утилита для тех случаев, когда у тебя есть просто текстовый файл
вида "слово :: определение" (по одной паре на строку) — например, если
достаёшь текст из другого источника (PDF/DJVU после OCR, ручные заметки
и т.п.) — и нужно превратить его в dictionary.json для online-словаря
(index.html).

Формат входного файла (UTF-8), каждая строка — одна статья:

    борода :: Волосы на нижней части лица.
    кабак :: Питейное заведение низшего разряда (устар.).

Разделитель "::" можно поменять через --sep.
Пустые строки и строки, начинающиеся с "#", пропускаются (можно
использовать "#" для комментариев/заметок в исходнике).

Использование:
    python3 convert_text_pairs.py input.txt dictionary.json
    python3 convert_text_pairs.py input.txt dictionary.json --sep "|"
    python3 convert_text_pairs.py input.txt dictionary.json --merge dictionary.json
        (--merge: подмешать новые статьи в уже существующий dictionary.json,
         не затирая его — удобно для постепенного пополнения словаря)
"""
import json
import sys
import argparse


def make_key(word):
    """Ключ для поиска: нижний регистр, без ударений/лишних пробелов."""
    return word.strip().lower().replace("\u0301", "").replace("+", "")


def make_display(word):
    """Слово для показа: первая буква заглавная, ударение (если было
    проставлено символом '+' перед гласной, как в exception_dictionary.txt
    из проекта StressRNN) переводится в обычный юникодный акут."""
    w = word.strip().replace("+", "\u0301")
    return w[0].upper() + w[1:] if w else w


def parse_file(path, sep):
    records = []
    skipped = 0
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue
            if sep not in line:
                print(f"[строка {lineno}] нет разделителя '{sep}', пропущено: {line[:60]!r}")
                skipped += 1
                continue
            word, definition = line.split(sep, 1)
            word = word.strip()
            definition = definition.strip()
            if not word or not definition:
                print(f"[строка {lineno}] пустое слово или определение, пропущено")
                skipped += 1
                continue
            records.append({
                "word": make_display(word),
                "key": make_key(word),
                "def": definition,
                "review": False,   # ручной ввод считаем проверенным; поставь True при необходимости
            })
    return records, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="текстовый файл 'слово :: определение'")
    ap.add_argument("output", help="куда сохранить dictionary.json")
    ap.add_argument("--sep", default="::", help="разделитель слова и определения (по умолчанию '::')")
    ap.add_argument("--merge", default=None, help="существующий dictionary.json, в который нужно домешать новые статьи")
    args = ap.parse_args()

    records, skipped = parse_file(args.input, args.sep)
    print(f"Разобрано статей: {len(records)}, пропущено строк: {skipped}")

    if args.merge:
        with open(args.merge, encoding="utf-8") as f:
            existing = json.load(f)
        existing_keys = {r["key"] for r in existing}
        added = 0
        for r in records:
            if r["key"] in existing_keys:
                continue  # не затираем то, что уже есть - обнови вручную при необходимости
            existing.append(r)
            existing_keys.add(r["key"])
            added += 1
        out = existing
        print(f"Добавлено новых статей в существующий словарь: {added}")
    else:
        out = records

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Сохранено {len(out)} статей в {args.output}")


if __name__ == "__main__":
    main()
