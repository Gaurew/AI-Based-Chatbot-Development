import re
from typing import Optional


def parse_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)", text.replace(",", ""))
    return int(m.group(1)) if m else None


