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


def build_qa_training_store_generation_prompt(
    *, eval_input: str, required_artifacts: list[dict[str, str]]
) -> str:
    if not eval_input.strip() or not required_artifacts:
        raise ValueError("eval_input and required_artifacts must be non-empty")
    rows: list[str] = []
    for index, item in enumerate(required_artifacts):
        if not isinstance(item, dict) or set(item) != {"skill", "kind", "scope"}:
            raise ValueError(f"required_artifacts[{index}] has an invalid shape")
        if any(
            not isinstance(item[key], str) or not item[key].strip()
            for key in ("skill", "kind", "scope")
        ):
            raise ValueError(f"required_artifacts[{index}] has an invalid field")
        rows.append(f"| `{item['skill']}` | `{item['kind']}` | `{item['scope']}` |")
    contract = "\n".join(rows)
    enriched_input = f"""{eval_input}

# 固定シナリオのartifact-index登録契約

各必須成果物を `artifact-index.json` に登録するときは、下表の `skill`、`kind`、`scope` を正確に使用してください。`routing[]`にも、下表の各 `skill` と同じ `scope` を持つ行を1つずつ登録し、statusと理由を実際の状態に合わせ、実在する成果物のIDを`artifact_ids`へ結び付けてください。このメタデータは成果物本文やrouting statusを指定しません。`schema_version` は文字列 `"1"` ではなくJSON numberの `1` にしてください。実在する成果物だけを登録し、未完了・blockedの工程は実際の状態で記録してください。

| skill | kind | scope |
| --- | --- | --- |
{contract}
"""
    return build_generation_prompt(skill="qa-workflow", eval_input=enriched_input)


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
