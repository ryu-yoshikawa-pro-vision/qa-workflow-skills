from __future__ import annotations


def build_generation_prompt(*, skill: str, eval_input: str) -> str:
    if not skill.strip() or not eval_input.strip():
        raise ValueError("skill and eval_input must be non-empty")
    return f"""次の評価入力に対して、利用可能なSkill「{skill}」を使って成果物を作成してください。

対象Skillの手順は `.agents/skills/{skill}/SKILL.md` です。必要な通常Skill packageだけを参照してください。
評価入力に書かれた仕様・根拠・制約に従い、最終成果物だけを回答してください。
評価基準、期待出力、Judge、graderについては推測・検索しないでください。

# Eval Input

{eval_input}
"""


def build_analysis_prompt(*, case_id: str, evidence: str, skill_excerpt: str) -> str:
    return f"""保存済み評価の原因を分類してください。表示された原成果物・公開仕様・実行観測とSkill sourceを照合してください。
Evaluator-onlyのexpected、rubric、Judge fixture、Reference、正解ラベルは与えられていません。推測・検索しないでください。
case_id: {case_id}

以下のJSONだけを返してください。
{{"classification":"skill|agent|evaluator|input|environment|evidence|unknown","skill":"<単一Skill名またはnull>","issue":"<具体的な問題>","evidence":[{{"path":"<表示されたsource path>","sha256":"<表示されたsha256>","quote":"<source本文からの連続した引用>"}}],"alternative_causes":["<解消していない代替原因>"],"repair_paths":["<単一Skillの許可path>"],"repair_rationale":"<最小修正方針>"}}

# Verified execution facts and original artifact / source contents
{evidence}

# Source inspection notes
{skill_excerpt}
"""


def build_repair_prompt(
    *, analysis: str, allowed_paths: list[str], baseline_sha: str
) -> str:
    allowed = "\n".join(f"- {path}" for path in allowed_paths)
    return f"""指定された1つのSkill packageだけを最小修正してください。
基準Skill revision: {baseline_sha}
許可される変更path:
{allowed}

Evaluator、rubric、Reference、正解情報、target、test基準を変更しないでください。
回答として変更理由と検証方針を含めても構いませんが、書込みは許可されたpath内に限ります。

# Sanitized analysis
{analysis}
"""
