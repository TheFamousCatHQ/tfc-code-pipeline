def lcfirst(s: str) -> str:
    if not s:
        return s  # Return empty string as is
    return s[0].lower() + s[1:]
