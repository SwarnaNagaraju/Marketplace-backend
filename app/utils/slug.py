import re
import uuid


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return f"{slug}-{uuid.uuid4().hex[:8]}"
