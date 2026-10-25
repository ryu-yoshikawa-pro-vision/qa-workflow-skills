#!/usr/bin/env python3
"""質問JSONからオフライン単一HTMLフォームを生成する。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "assets" / "form_template.html"
APPLICATION = ROOT / "assets" / "form.js"
DATA_MARKER = "__QUESTIONNAIRE_JSON__"
JS_MARKER = "__FORM_APP_JS__"
IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
CHOICE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,31}$")


class FormError(ValueError):
    """質問JSONの入力エラー。"""


def obj(value: object, path: str) -> dict:
    if not isinstance(value, dict):
        raise FormError(f"{path}: JSONオブジェクトが必要です")
    return value


def txt(value: object, path: str, *, optional: bool = False, limit: int = 20000) -> str:
    if value is None and optional:
        return ""
    if not isinstance(value, str) or (not optional and not value.strip()):
        raise FormError(f"{path}: 空でない文字列が必要です")
    if len(value) > limit:
        raise FormError(f"{path}: {limit}文字以内で指定してください")
    return value


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise FormError(f"JSONキーが重複しています: {key}")
        result[key] = value
    return result


def _question_hash(question: dict) -> str:
    # 表示番号だけの変更では回答の意味を変えない。
    relevant = {
        key: question.get(key)
        for key in (
            "id",
            "title",
            "group",
            "priority",
            "context",
            "recommendation",
            "defaultMultiple",
            "choices",
        )
    }
    canonical = json.dumps(
        relevant, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate(data: object) -> dict:
    form = obj(data, "ルート")
    if type(form.get("schemaVersion")) is not int or form["schemaVersion"] != 1:
        raise FormError("schemaVersion: 数値の1が必要です")
    form_id = txt(form.get("formId"), "formId", limit=64)
    if not IDENTIFIER.fullmatch(form_id):
        raise FormError("formId: 英数字・ハイフン・アンダースコアで指定してください")
    txt(form.get("title"), "title", limit=200)
    for field in ("subtitle", "description", "notice"):
        txt(form.get(field), field, optional=True)
    output = obj(form.get("output"), "output")
    txt(output.get("heading"), "output.heading", limit=200)
    txt(output.get("context"), "output.context", optional=True)
    name = txt(output.get("filename"), "output.filename", limit=120)
    if (
        not name.lower().endswith(".md")
        or name in (".md", "..md")
        or "/" in name
        or "\\" in name
        or any(c in '<>:"|?*' or ord(c) < 32 for c in name)
    ):
        raise FormError("output.filename: ディレクトリを含まない.md名が必要です")
    questions = form.get("questions")
    if not isinstance(questions, list) or not 1 <= len(questions) <= 500:
        raise FormError("questions: 1～500問の配列が必要です")
    seen = set()
    for i, entry in enumerate(questions):
        path = f"questions[{i}]"
        q = obj(entry, path)
        qid = txt(q.get("id"), path + ".id", limit=64)
        if not IDENTIFIER.fullmatch(qid):
            raise FormError(f"{path}.id: 不正な識別子です")
        if qid in seen:
            raise FormError(f"{path}.id: 重複しています: {qid}")
        seen.add(qid)
        for key in ("title", "group"):
            txt(q.get(key), f"{path}.{key}", limit=1000)
        for key in ("number", "priority", "context", "recommendation"):
            txt(q.get(key), f"{path}.{key}", optional=True)
        if "defaultMultiple" in q and not isinstance(q["defaultMultiple"], bool):
            raise FormError(f"{path}.defaultMultiple: 真偽値が必要です")
        choices = q.setdefault("choices", [])
        if not isinstance(choices, list) or len(choices) > 26:
            raise FormError(f"{path}.choices: 0～26件の配列が必要です")
        option_ids = set()
        for j, item in enumerate(choices):
            cp = f"{path}.choices[{j}]"
            choice = obj(item, cp)
            cid = txt(choice.get("id"), cp + ".id", limit=32)
            if not CHOICE_ID.fullmatch(cid):
                raise FormError(f"{cp}.id: 不正な識別子です")
            txt(choice.get("label"), cp + ".label", limit=5000)
            if cid in option_ids:
                raise FormError(f"{cp}.id: 重複しています: {cid}")
            option_ids.add(cid)
    return form


def build(form: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    script = APPLICATION.read_text(encoding="utf-8")
    if template.count(DATA_MARKER) != 1 or template.count(JS_MARKER) != 1:
        raise FormError("HTMLテンプレートの埋め込み位置が不正です")
    if "</script" in script.lower():
        raise FormError("form.jsにscript終了タグがあります")
    embedded = {
        **form,
        "questions": [
            {**question, "_definitionHash": _question_hash(question)}
            for question in form["questions"]
        ],
    }
    payload = json.dumps(embedded, ensure_ascii=False, separators=(",", ":"))
    for old, new in (
        ("<", r"\u003c"),
        (">", r"\u003e"),
        ("&", r"\u0026"),
        ("\u2028", r"\u2028"),
        ("\u2029", r"\u2029"),
    ):
        payload = payload.replace(old, new)
    return template.replace(JS_MARKER, script).replace(DATA_MARKER, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="質問JSONから単一HTMLを生成")
    parser.add_argument("--input", "-i", type=Path, required=True)
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only and args.output is None:
        parser.error("--outputまたは--validate-onlyが必要です")
    try:
        form = validate(
            json.loads(
                args.input.read_text(encoding="utf-8-sig"),
                object_pairs_hook=_unique_keys,
            )
        )
        if args.validate_only:
            print(f"検証成功: {len(form['questions'])}問")
            return 0
        if (
            args.output.resolve()
            in (args.input.resolve(), TEMPLATE.resolve(), APPLICATION.resolve())
            or args.output.suffix.lower() != ".html"
        ):
            raise FormError("--outputは入力やテンプレートと異なる.htmlを指定")
        html = build(form)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
        print(f"生成成功: {args.output}（{len(form['questions'])}問）")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, FormError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
