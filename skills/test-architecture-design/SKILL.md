---
name: test-architecture-design
description: QA要求・製品構成・重要品質特性に対し、テストレベル／タイプ・方式・環境・データと検証分担を全体設計する。「テスト方式・レベル割当・検証分担・環境・データの設計や再評価」を求められたら、自分で設計する前に必ずこのSkillを読み込む。Product Risk採点や個別TCN／CI／TCの設計には使用しない。
---

# テストアーキテクチャ設計

## 実行契約

1. 実行前に`references/guidance.md`と`references/data-contract.md`を読み、割当優先順位、source currentness、承認、局所影響の規則に従います。
2. 本Skillが所有するのはQA全体の対象アイテム／品質特性／リスクに対するテストレベル・タイプ・方式・環境・データ・検証分担です。Product Riskの正本は`test-analysis`、E2E自動化価値は`e2e-test-selection`、Playwright実装可能性は`e2e-test-inspection`、具体的なTCN／CI／TCは各既存設計Skillです。
3. 入力のowner・artifact/source ref・revision・scope・currentnessを記録します。開発feature／test item／condition候補が未提供でも、currentな既存仕様や既存QA要求からできる範囲を扱い、他ownerのIDやschemaを推測して作りません。
4. テストレベルの優先順位は、案件／利用者の明示指定、承認済みarchitecture割当、いずれもなければ`test-analysis`の既定system testです。矛盾は解決元に戻し、複数レベルを一つへ丸めません。
5. 環境・データ・ツール・測定方法が未確定なら対象scopeをblockedまたは未確定にします。実行可能・自動化済みと推測しません。
6. Riskや既存の正式設計を更新せず、割当変更が及ぶRisk・TR／TCN／CI／TC・実行準備だけを要再確認としてhandoffします。無関係なcurrent成果物を保持します。
7. 承認前のarchitecture案を下流の確定入力として使いません。保存・承認providerが未接続なら草案のまま扱います。
8. 既存TCからの直接実行、計画だけの開始、QA要求・報告の途中開始を妨げません。E2E選定・Regression Run・workflow stateを二重管理しません。
9. 最終出力前に入力・割当・依存影響・未解決事項を`references/guidance.md`の品質ゲートで確認します。意味判断が必要な不一致は推測補完しません。

## 入出力

- **入力**: QA要求、current仕様・Product Risk、利用可能ならfeature／item／condition refs、製品構成、品質特性、環境／data／既存testware、既存architecture。
- **出力**: requirement／target別のlevel・type・方式・環境・data・検証分担・制約と根拠、承認・revision・依存ref、変更時の局所再確認先。
- **開始範囲**: 全体architectureの作成、特定品質特性／対象の割当変更、既存割当のcurrentness確認。

## 正規出力

`assets/output-template.md`の形式を使います。割当IDはartifact系列内で安定させ、ref・revision・scopeと合わせます。環境準備や保存先が未接続の状態を成功としません。

## 次の担当

- 計画・source inventory・monitoring: `test-management`
- Product Risk: `test-analysis`
- E2E価値／実装可能性: `e2e-test-selection` / `e2e-test-inspection`
- 個別正式設計: `test-requirement-design` / `test-condition-design` / `test-case-design`
