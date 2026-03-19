"""WeChat Official Account article formatter: Markdown → styled HTML."""
from __future__ import annotations

import re
from pathlib import Path

from src.core.config import CONFIG_DIR

# Domain-specific style mappings
DOMAIN_STYLES = {
    "finance": {
        "primary_color": "#1a365d",
        "accent_color": "#3182ce",
        "heading_color": "#1a365d",
        "bg_color": "#f7fafc",
        "font": "'PingFang SC', 'Hiragino Sans GB', sans-serif",
    },
    "geopolitics": {
        "primary_color": "#2d3436",
        "accent_color": "#d63031",
        "heading_color": "#2d3436",
        "bg_color": "#f8f9fa",
        "font": "'PingFang SC', 'Songti SC', serif",
    },
    "mystical": {
        "primary_color": "#2d1b69",
        "accent_color": "#9b59b6",
        "heading_color": "#2d1b69",
        "bg_color": "#f5f0ff",
        "font": "'PingFang SC', 'Kaiti SC', serif",
    },
    "knowledge": {
        "primary_color": "#2c3e50",
        "accent_color": "#2980b9",
        "heading_color": "#2c3e50",
        "bg_color": "#fafafa",
        "font": "'PingFang SC', 'Hiragino Sans GB', sans-serif",
    },
}


def format_wechat_article(
    title: str,
    markdown_text: str,
    domain: str = "knowledge",
    disclaimers: list[str] | None = None,
    images: list[str] | None = None,
) -> str:
    """Convert Markdown to WeChat-compatible styled HTML."""
    style = DOMAIN_STYLES.get(domain, DOMAIN_STYLES["knowledge"])

    # Convert markdown to HTML (simple conversion)
    html_body = _markdown_to_html(markdown_text)

    # Strip emotion markers
    html_body = re.sub(r'\[emotion:\w+\]', '', html_body)
    html_body = re.sub(r'\[/emotion\]', '', html_body)
    html_body = re.sub(r'\[pause:[\d.]+s?\]', '', html_body)

    # Build disclaimer section
    disclaimer_html = ""
    if disclaimers:
        disclaimer_html = '<section style="margin-top:40px;padding:15px;background:#f0f0f0;border-radius:8px;font-size:12px;color:#888;">'
        for d in disclaimers:
            disclaimer_html += f"<p>{d}</p>"
        disclaimer_html += "</section>"

    # Assemble full article
    article = f"""<section style="max-width:677px;margin:0 auto;padding:20px;font-family:{style['font']};line-height:1.8;color:#333;">

<h1 style="font-size:22px;color:{style['heading_color']};font-weight:bold;margin-bottom:20px;text-align:center;">{title}</h1>

<section style="font-size:15px;color:#555;">
{html_body}
</section>

{disclaimer_html}

</section>"""

    return article


def _markdown_to_html(text: str) -> str:
    """Simple Markdown to HTML conversion for WeChat compatibility."""
    lines = text.split("\n")
    html_lines = []
    in_list = False
    in_code = False

    for line in lines:
        stripped = line.strip()

        # Code blocks
        if stripped.startswith("```"):
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                html_lines.append('<pre style="background:#f5f5f5;padding:12px;border-radius:4px;overflow-x:auto;font-size:13px;"><code>')
                in_code = True
            continue

        if in_code:
            html_lines.append(stripped)
            continue

        # Headers
        if stripped.startswith("### "):
            html_lines.append(f'<h3 style="font-size:17px;color:#333;margin:25px 0 10px;font-weight:bold;">{stripped[4:]}</h3>')
        elif stripped.startswith("## "):
            html_lines.append(f'<h2 style="font-size:18px;color:#333;margin:30px 0 12px;font-weight:bold;border-left:4px solid #3182ce;padding-left:10px;">{stripped[3:]}</h2>')
        elif stripped.startswith("# "):
            html_lines.append(f'<h1 style="font-size:20px;color:#333;margin:30px 0 15px;font-weight:bold;">{stripped[2:]}</h1>')
        # Bold
        elif stripped.startswith("**") and stripped.endswith("**"):
            html_lines.append(f'<p style="font-weight:bold;color:#333;">{stripped[2:-2]}</p>')
        # List items
        elif stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:]
            html_lines.append(f'<p style="padding-left:15px;">• {_inline_format(content)}</p>')
        # Numbered list
        elif re.match(r'^\d+\.\s', stripped):
            content = re.sub(r'^\d+\.\s', '', stripped)
            num = re.match(r'^(\d+)', stripped).group(1)
            html_lines.append(f'<p style="padding-left:15px;">{num}. {_inline_format(content)}</p>')
        # Blockquote
        elif stripped.startswith("> "):
            html_lines.append(f'<blockquote style="border-left:3px solid #ddd;padding-left:12px;color:#666;margin:10px 0;">{stripped[2:]}</blockquote>')
        # Empty line
        elif not stripped:
            html_lines.append("<p>&nbsp;</p>")
        # Regular paragraph
        else:
            html_lines.append(f"<p>{_inline_format(stripped)}</p>")

    return "\n".join(html_lines)


def _inline_format(text: str) -> str:
    """Apply inline Markdown formatting."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`(.+?)`', r'<code style="background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:13px;">\1</code>', text)
    return text
