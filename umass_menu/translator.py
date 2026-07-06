"""菜名翻译：优先 Anthropic API（需 ANTHROPIC_API_KEY），否则走 claude CLI 无头模式。

所有译名写入 dishes.name_zh 作为永久缓存，每个菜名只翻译一次。
"""
import json
import os
import re
import subprocess

from . import config

PROMPT = """你是 UMass Amherst 大学食堂菜单的翻译助手。把下面的英文菜名翻译成简体中文。
要求：
- 意译为主，让中国学生一眼看懂是什么菜；常见外国菜用通行中文叫法（如 Pad Thai → 泰式炒河粉）
- 缩写说明：w/ = with，GF = 无麸质，Rstd = Roasted，Sub = Substitute
- 译名简洁，不加解释
- 只输出一个 JSON 对象，格式 {"英文菜名": "中文译名", ...}，键必须与输入完全一致，不要输出任何其他文字

菜名列表：
%s"""


def _extract_json(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object in response: {text[:200]!r}")
    return json.loads(m.group(0))


def _via_api(prompt):
    import urllib.request
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        })
    resp = json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8"))
    return resp["content"][0]["text"]


def _via_cli(prompt):
    proc = subprocess.run(
        [config.CLAUDE_CLI, "-p", "--model", config.CLAUDE_MODEL],
        input=prompt, capture_output=True, text=True, encoding="utf-8",
        timeout=config.TRANSLATE_TIMEOUT, shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {proc.stderr[:300]}")
    return proc.stdout


def translate(names, log=print):
    """翻译一组英文菜名，返回 {en: zh}。失败的批次跳过，下次运行再补。"""
    use_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
    result = {}
    for i in range(0, len(names), config.TRANSLATE_CHUNK):
        chunk = names[i:i + config.TRANSLATE_CHUNK]
        prompt = PROMPT % json.dumps(chunk, ensure_ascii=False, indent=0)
        try:
            text = _via_api(prompt) if use_api else _via_cli(prompt)
            mapping = _extract_json(text)
            got = {en: zh.strip() for en, zh in mapping.items()
                   if en in chunk and isinstance(zh, str) and zh.strip()}
            result.update(got)
            log(f"  翻译批次 {i // config.TRANSLATE_CHUNK + 1}: "
                f"{len(got)}/{len(chunk)} 条成功")
        except Exception as e:
            log(f"  翻译批次 {i // config.TRANSLATE_CHUNK + 1} 失败（跳过，下次补翻）: {e}")
    return result
