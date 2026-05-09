"""TMDB API client - Auto fetch poster, rating, info drama."""

import httpx
from config import TMDB_API_KEY, TMDB_BASE_URL, TMDB_IMAGE_URL


async def search_tmdb(query: str, media_type: str = "tv"):
    """Search drama/movie di TMDB.
    
    Args:
        query: Judul yang dicari
        media_type: 'tv' untuk serial, 'movie' untuk film
    
    Returns:
        List of results dengan poster_url, rating, overview, dll
    """
    if not TMDB_API_KEY:
        return []

    url = f"{TMDB_BASE_URL}/search/{media_type}"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "id-ID",  # Bahasa Indonesia
        "page": 1,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", [])[:8]:  # Max 8 results
            title = item.get("name") or item.get("title") or ""
            original_title = item.get("original_name") or item.get("original_title") or ""
            poster_path = item.get("poster_path") or ""
            poster_url = f"{TMDB_IMAGE_URL}{poster_path}" if poster_path else ""

            results.append({
                "tmdb_id": item.get("id"),
                "title": title,
                "original_title": original_title,
                "overview": item.get("overview", ""),
                "poster_url": poster_url,
                "rating": item.get("vote_average", 0),
                "vote_count": item.get("vote_count", 0),
                "year": _extract_year(item),
                "genre_ids": item.get("genre_ids", []),
                "media_type": media_type,
            })

        return results
    except Exception as e:
        print(f"TMDB search error: {e}")
        return []


async def get_tmdb_detail(tmdb_id: int, media_type: str = "tv"):
    """Get detail lengkap dari TMDB."""
    if not TMDB_API_KEY:
        return None

    url = f"{TMDB_BASE_URL}/{media_type}/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "id-ID",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            item = resp.json()

        title = item.get("name") or item.get("title") or ""
        original_title = item.get("original_name") or item.get("original_title") or ""
        poster_path = item.get("poster_path") or ""
        poster_url = f"{TMDB_IMAGE_URL}{poster_path}" if poster_path else ""

        genres = ", ".join([g["name"] for g in item.get("genres", [])])

        return {
            "tmdb_id": item.get("id"),
            "title": title,
            "original_title": original_title,
            "overview": item.get("overview", ""),
            "poster_url": poster_url,
            "rating": item.get("vote_average", 0),
            "vote_count": item.get("vote_count", 0),
            "year": _extract_year(item),
            "genres": genres,
            "status": item.get("status", ""),
            "total_episodes": item.get("number_of_episodes", 0),
            "total_seasons": item.get("number_of_seasons", 0),
            "media_type": media_type,
        }
    except Exception as e:
        print(f"TMDB detail error: {e}")
        return None


async def get_genre_names(genre_ids: list, media_type: str = "tv"):
    """Convert genre IDs ke nama genre."""
    if not TMDB_API_KEY:
        return ""

    url = f"{TMDB_BASE_URL}/genre/{media_type}/list"
    params = {"api_key": TMDB_API_KEY, "language": "id-ID"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        genre_map = {g["id"]: g["name"] for g in data.get("genres", [])}
        names = [genre_map.get(gid, "") for gid in genre_ids if gid in genre_map]
        return ", ".join(names)
    except Exception:
        return ""


def _extract_year(item):
    """Extract year from TMDB item."""
    date = item.get("first_air_date") or item.get("release_date") or ""
    return date[:4] if date else ""
