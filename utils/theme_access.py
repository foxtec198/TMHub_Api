"""Regras de liberação das identidades visuais do TM Hub."""

CUSTOM_THEMES = frozenset({
    "cyberpunk", "pride", "christmas", "aurora", "ocean",
    "sunset", "forest", "terminal", "paper", "muertos",
})
DEFAULT_THEME = "tmhub"


def can_use_custom_themes(user):
    """Administradores e usuários liberados no banco podem usar temas extras."""
    return bool(
        user
        and (
            str(getattr(user, "role", "") or "").upper() == "ADMIN"
            or bool(getattr(user, "temas_extras_liberados", False))
        )
    )


def available_themes_for(user):
    return [DEFAULT_THEME, *sorted(CUSTOM_THEMES)] if can_use_custom_themes(user) else [DEFAULT_THEME]


def effective_theme_for(user):
    stored_theme = str(getattr(user, "tema", "") or DEFAULT_THEME).lower()
    if stored_theme in CUSTOM_THEMES and not can_use_custom_themes(user):
        return DEFAULT_THEME
    return stored_theme if stored_theme in CUSTOM_THEMES | {DEFAULT_THEME} else DEFAULT_THEME
