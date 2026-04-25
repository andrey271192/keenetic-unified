"""Системный блок «автор продукта»: GitHub, Boosty, Ozon Bank (СБП), Telegram.
URL не в шаблонах в открытом виде (b64 + сборка в рантайме)."""

from __future__ import annotations

import base64
import html


def _u(b64: str) -> str:
    return base64.b64decode(b64.encode("ascii")).decode("ascii")


_GH = _u("aHR0cHM6Ly9naXRodWIuY29tL2FuZHJleTI3MTE5Mg==")
_BZ = _u("aHR0cHM6Ly9ib29zdHkudG8vYW5kcmV5MjcvZG9uYXRl")
_OZ = _u(
    "aHR0cHM6Ly9maW5hbmNlLm96b24ucnUvYXBwcy9zYnAvb3pvbmJhbmtwYXkvMDE5ZGMyMDAtMmE1ZC03OTMxLWE2MTktNzgyZDI4NWY2Nzk4"
)


def brand_bar_html(telegram_username: str) -> str:
    u = (telegram_username or "Iot_andrey").lstrip("@")
    tg = f"https://t.me/{u}"
    safe_u = html.escape(u, quote=True)
    return (
        "<style id=\"ku-brand\">#ku-brand{position:fixed;bottom:10px;left:12px;z-index:90;"
        "max-width:min(96vw,720px);font-size:11px;font-weight:600;letter-spacing:.02em;"
        "color:#86868b;opacity:.92;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;line-height:1.3}"
        "#ku-brand a{color:#a1a1a6;text-decoration:none;border-bottom:1px solid rgba(255,255,255,.12);"
        "transition:color .15s,border-color .15s}"
        "#ku-brand a:hover{color:#0a84ff;border-bottom-color:#0a84ff}"
        "#ku-brand .ku-l{color:#6e6e73;font-weight:500;margin-right:2px}</style>"
        '<div id="ku-brand" lang="ru"><span class="ku-l">автор:</span>'
        f'<a href="{_GH}" target="_blank" rel="noopener noreferrer">GitHub</a><span>·</span>'
        f'<a href="{_BZ}" target="_blank" rel="noopener noreferrer">Boosty</a><span>·</span>'
        f'<a href="{_OZ}" target="_blank" rel="noopener noreferrer" title="Поддержка проекта (Ozon Bank, СБП)">'
        "Поддержка</a><span>·</span>"
        f'<a href="{html.escape(tg, quote=True)}" target="_blank" rel="noopener noreferrer">'
        f"@{safe_u}</a></div>"
    )


def inject_brand_html(page_html: str, telegram_username: str) -> str:
    b = brand_bar_html(telegram_username)
    if "</body>" in page_html:
        return page_html.replace("</body>", f"{b}\n</body>", 1)
    return page_html + b
