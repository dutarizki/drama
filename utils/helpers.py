"""Utility/helper functions."""

from config import STATUS_ONGOING


def format_drama_info(drama, episode_count=0):
    """Format drama info dengan rating & poster."""
    status_emoji = "🟢" if drama.get("status") == STATUS_ONGOING else "🔵"
    rating = drama.get("rating", 0)
    stars = _rating_stars(rating)

    text = f"🎬 *{esc(drama['title'])}*\n"
    if drama.get("original_title") and drama["original_title"] != drama["title"]:
        text += f"🔤 {esc(drama['original_title'])}\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"

    if rating:
        text += f"⭐ Rating: {rating:.1f}/10 {stars}\n"
    if drama.get("year"):
        text += f"📅 Tahun: {esc(drama['year'])}\n"
    if drama.get("genre"):
        text += f"🎭 Genre: {esc(drama['genre'])}\n"
    text += f"📊 Status: {status_emoji} {esc(drama.get('status', 'Unknown'))}\n"
    text += f"📺 Episode tersedia: {episode_count}\n"

    if drama.get("description"):
        desc = drama["description"][:300]
        if len(drama["description"]) > 300:
            desc += "..."
        text += f"\n📝 {esc(desc)}\n"

    return text


def _rating_stars(rating):
    """Convert rating to star display."""
    if not rating:
        return ""
    filled = int(rating / 2)
    return "★" * filled + "☆" * (5 - filled)


def esc(text):
    """Escape special characters for MarkdownV2."""
    if not text:
        return ""
    special = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for c in special:
        text = str(text).replace(c, f'\\{c}')
    return text
