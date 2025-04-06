from typing import Optional

def sanitize_html(text: str) -> str:
    """Basic HTML sanitization"""
    if not text:
        return ""
    return (text.replace('<', '&lt;')
               .replace('>', '&gt;')
               .replace('"', '&quot;')
               .replace("'", '&#x27;'))

def format_url(url: str) -> str:
    """Format URLs consistently"""
    return url.strip().rstrip('/')

def create_info_box(content: str, title: Optional[str] = None) -> str:
    """Creates a styled info box"""
    title_html = f"<h3>{title}</h3>" if title else ""
    return f"""
        <div class="info-box">
            {title_html}
            {content}
        </div>
    """