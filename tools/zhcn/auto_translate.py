#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_translate.py - Translate newly-added untranslated strings using an
OpenAI-compatible chat completion API.

Requires environment variables:
  LLM_API_KEY   API key (create the repository secret with the same name to
                enable automatic translation during upstream sync)
  LLM_BASE_URL  API base URL (default https://open.bigmodel.cn/api/paas/v4)
  LLM_MODEL     model name (required when the key is set)

Without LLM_API_KEY the script is a no-op: untranslated strings stay English
and the coverage report lists them for manual translation.
"""

import argparse
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(__file__)

GLOSSARY_RULES = """
1. 术语：process=进程、handle=句柄、service=服务、module=模块、thread=线程、token=令牌、
   privilege=特权、dump=转储、terminate=终止、suspend=挂起、resume=恢复、kernel=内核、
   working set=工作集、commit charge=提交内存、private bytes=专用字节、driver=驱动程序、
   volume=卷、partition=分区、registry=注册表、startup=启动、tray=托盘、plugin=插件。
2. "System Informer" 一律译为 "sys_info"。
3. 助记符格式固定为 中文(&字母)，保留原字母；\\t 后的快捷键原样保留；省略号用 ...。
4. 格式占位符（%s、%lu、%I64u 等）数量、类型、顺序绝对不能变。
5. 按钮/列名译文要短；句子用中文标点。KB/MB/GB/ms 等单位保留英文。
6. 翻译要自然地道，像微软官方中文版，禁止机翻腔。
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=os.path.join(HERE, "manifest.json"))
    ap.add_argument("--translation", default=os.path.join(HERE, "zh-CN.json"))
    ap.add_argument("--glossary", default=os.path.join(HERE, "glossary.md"))
    ap.add_argument("--max", type=int, default=400)
    args = ap.parse_args()

    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        print("LLM_API_KEY not set; skipping automatic translation")
        return 0

    base_url = os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
    model = os.environ.get("LLM_MODEL")
    if not model:
        print("error: LLM_MODEL is required when LLM_API_KEY is set")
        return 1

    sys.path.insert(0, HERE)
    from check_translation import is_keep_english  # noqa: E402

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)
    with open(args.translation, encoding="utf-8") as f:
        table = json.load(f)
    with open(args.glossary, encoding="utf-8") as f:
        glossary = f.read()

    strings = table["strings"]
    pending = []
    seen = set()
    for entry in manifest["unique_strings"]:
        en = entry["english"]
        if en in seen or is_keep_english(en) or not re.search(r"[A-Za-z]", en):
            continue
        seen.add(en)
        if strings.get(en) in (None, en):
            pending.append(en)

    if not pending:
        print("nothing to translate")
        return 0

    pending = pending[:args.max]
    print(f"translating {len(pending)} strings with {model}")

    batch = pending[:80]
    prompt = (
        "你是 Windows 软件本地化专家。将下面 JSON 数组中的每个英文界面字符串翻译为简体中文，"
        "输出一个 JSON 对象（key=原文，value=译文）。规则：\n"
        + GLOSSARY_RULES
        + "\n术语表（节选）：\n"
        + glossary[:3000]
        + "\n待翻译：\n"
        + json.dumps(batch, ensure_ascii=False)
    )

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }).encode("utf-8")

    req = urllib.request.Request(
        base_url + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.load(resp)
        content = result["choices"][0]["message"]["content"]
        content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.M).strip()
        translated = json.loads(content)
    except Exception as exc:
        print(f"error: automatic translation failed: {exc}")
        return 1

    accepted = 0
    for en, zh in translated.items():
        if not isinstance(zh, str) or not zh or zh == en or en not in seen:
            continue
        if en.count("\t") != zh.count("\t"):
            continue
        strings[en] = zh
        accepted += 1

    if accepted:
        table["strings"] = dict(sorted(strings.items()))
        with open(args.translation, "w", encoding="utf-8") as f:
            json.dump(table, f, ensure_ascii=False, indent=2)
            f.write("\n")

    print(f"accepted {accepted}/{len(batch)} translations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
