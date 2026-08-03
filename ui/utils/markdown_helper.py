import re

def render_markdown_to_html(md_text: str) -> str:
    if not md_text:
        return ""
    
    text = md_text.replace("\r\n", "\n")
    
    try:
        import markdown
        html = markdown.markdown(
            text,
            extensions=['tables', 'fenced_code', 'sane_lists']
        )
    except Exception:
        html = _custom_markdown_parser(text)

    return _apply_dark_theme_styles(html)


def _custom_markdown_parser(text: str) -> str:
    lines = text.strip().split('\n')
    out = []
    in_table = False
    in_list = False
    
    for line in lines:
        raw = line.strip()
        
        # Horizontal rule
        if raw in ('---', '***', '___'):
            if in_list: out.append('</ul>'); in_list = False
            if in_table: out.append('</tbody></table>'); in_table = False
            out.append('<hr/>')
            continue

        # Table row
        if raw.startswith('|') and raw.endswith('|'):
            if in_list: out.append('</ul>'); in_list = False
            cells = [c.strip() for c in raw[1:-1].split('|')]
            if all(set(c).issubset({'-', ':', ' '}) for c in cells):
                continue  # Header separator line
            if not in_table:
                in_table = True
                out.append('<table>')
                out.append('<thead><tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr></thead><tbody>')
            else:
                out.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
            continue
        elif in_table:
            out.append('</tbody></table>')
            in_table = False

        # List item
        if raw.startswith('- ') or raw.startswith('* '):
            if not in_list:
                in_list = True
                out.append('<ul>')
            item_text = raw[2:].strip()
            out.append(f'<li>{item_text}</li>')
            continue
        elif in_list:
            out.append('</ul>')
            in_list = False

        # Headings
        if raw.startswith('# '):
            out.append(f'<h1>{raw[2:]}</h1>')
        elif raw.startswith('## '):
            out.append(f'<h2>{raw[3:]}</h2>')
        elif raw.startswith('### '):
            out.append(f'<h3>{raw[4:]}</h3>')
        elif raw.startswith('***') and raw.endswith('***'):
            out.append(f'<p>*** {raw[3:-3].strip()} ***</p>')
        elif raw:
            out.append(f'<p>{raw}</p>')
        else:
            out.append('<br/>')

    if in_list: out.append('</ul>')
    if in_table: out.append('</tbody></table>')
    
    html = '\n'.join(out)
    
    # Inline formatting
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" height="16"/>', html)
    html = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', html)
    html = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', html)
    
    return html


def _apply_dark_theme_styles(html: str) -> str:
    # Headings
    html = re.sub(r'<h1>(.*?)</h1>', r'<h1 style="color: #4DB6AC; font-size: 18px; font-weight: bold; margin-top: 14px; margin-bottom: 6px; border-bottom: 1px solid #2B2C30; padding-bottom: 4px;">\1</h1>', html)
    html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="color: #64B5F6; font-size: 15px; font-weight: bold; margin-top: 12px; margin-bottom: 4px;">\1</h2>', html)
    html = re.sub(r'### (.*?)</h3>', r'<h3 style="color: #81C784; font-size: 13px; font-weight: bold; margin-top: 10px; margin-bottom: 2px;">\1</h3>', html)
    html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="color: #81C784; font-size: 13px; font-weight: bold; margin-top: 10px; margin-bottom: 2px;">\1</h3>', html)
    
    # Horizontal rules
    html = html.replace('<hr />', '<hr style="border: none; border-top: 1px solid #33363F; margin: 12px 0;"/>')
    html = html.replace('<hr>', '<hr style="border: none; border-top: 1px solid #33363F; margin: 12px 0;"/>')

    # Tables
    html = re.sub(r'<table>', r'<table border="0" cellspacing="0" cellpadding="6" style="width: 100%; margin: 8px 0; background-color: #141518; border: 1px solid #2B2C30; border-radius: 6px;">', html)
    html = re.sub(r'<thead>', r'<thead style="background-color: #252830; color: #4DB6AC; font-weight: bold;">', html)
    html = re.sub(r'<th>', r'<th style="color: #4DB6AC; padding: 6px 10px; border-bottom: 1px solid #2B2C30; text-align: left;">', html)
    html = re.sub(r'<td>', r'<td style="padding: 6px 10px; border-bottom: 1px solid #222226; color: #E0E0E0;">', html)

    # Lists & List Items
    html = re.sub(r'<ul>', r'<ul style="margin-top: 4px; margin-bottom: 8px; padding-left: 20px;">', html)
    html = re.sub(r'<li>', r'<li style="margin-bottom: 4px; color: #D0D0D0;">', html)

    # Links
    html = re.sub(r'<a href=', r'<a style="color: #4DB6AC; text-decoration: underline;" href=', html)

    # Highlight notice boxes (e.g. *** IF YOU'RE USING VERSION ... ***)
    html = re.sub(
        r'<p>\s*\*\*\*\s*(.*?)\s*\*\*\*\s*</p>',
        r'<p style="color: #FFA726; font-weight: bold; background-color: rgba(255,167,38,0.12); padding: 8px 12px; border-radius: 4px; border-left: 4px solid #FFA726; margin: 10px 0;">\1</p>',
        html
    )

    # Paragraphs
    html = re.sub(r'<p>', r'<p style="margin: 4px 0; line-height: 1.4; color: #E0E0E0;">', html)

    return html
