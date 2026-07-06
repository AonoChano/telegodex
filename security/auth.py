def sanitize_input(text: str, max_length: int = 4000) -> str:
    """Trim user input and bound its length before provider handling."""
    if len(text) > max_length:
        text = text[:max_length]
    return text.strip()
