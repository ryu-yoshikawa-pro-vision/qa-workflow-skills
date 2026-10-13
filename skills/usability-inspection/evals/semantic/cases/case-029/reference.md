# Expected semantic contract

LCP / CLS / INPを独自実装して作らず `measurement-unavailable` とし、固定probeでNavigation Timing / FCPの取得を継続すること。このcaseにはtask / actionがないため、interaction timingを捏造せず、実際のtask / inputが与えられた場合だけ測定対象にすること。
