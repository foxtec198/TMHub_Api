"""Regras de liberação das identidades visuais do TM Hub."""

CUSTOM_THEMES = frozenset({
    "cyberpunk", "pride", "christmas", "aurora", "ocean",
    "sunset", "forest", "terminal", "paper", "muertos",
})
DEFAULT_THEME = "tmhub"


def purchased_theme_codes(user):
    """Temas com compra ativa, sem acoplar o modelo de usuário ao catálogo."""
    if not user or getattr(user, "id", None) is None:
        return set()
    from models.marketplace import MarketplaceProduct, MarketplacePurchase

    rows = (
        MarketplacePurchase.query
        .join(MarketplaceProduct, MarketplaceProduct.id == MarketplacePurchase.produto_id)
        .filter(
            MarketplacePurchase.usuario_id == user.id,
            MarketplacePurchase.status == "concluida",
            MarketplaceProduct.categoria == "tema",
        )
        .with_entities(MarketplaceProduct.codigo)
        .all()
    )
    return {
        str(code).removeprefix("tema_")
        for (code,) in rows
        if code
    }


def can_use_theme(user, theme):
    theme = str(theme or DEFAULT_THEME).lower()
    if theme == DEFAULT_THEME:
        return True
    if theme not in CUSTOM_THEMES or not user:
        return False
    return bool(getattr(user, "temas_extras_liberados", False)) or theme in purchased_theme_codes(user)


def can_use_custom_themes(user):
    """Compatibilidade para consumidores que só precisam saber se há extras."""
    return bool(user and (getattr(user, "temas_extras_liberados", False) or purchased_theme_codes(user)))


def available_themes_for(user):
    if user and bool(getattr(user, "temas_extras_liberados", False)):
        return [DEFAULT_THEME, *sorted(CUSTOM_THEMES)]
    return [DEFAULT_THEME, *sorted(purchased_theme_codes(user) & CUSTOM_THEMES)]


def effective_theme_for(user):
    stored_theme = str(getattr(user, "tema", "") or DEFAULT_THEME).lower()
    if stored_theme in CUSTOM_THEMES and not can_use_theme(user, stored_theme):
        return DEFAULT_THEME
    return stored_theme if stored_theme in CUSTOM_THEMES | {DEFAULT_THEME} else DEFAULT_THEME
