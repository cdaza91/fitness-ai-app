import httpx
import os
from typing import Optional

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
API_KEY = os.getenv("YOUTUBE_API_KEY")

async def get_exercise_video_id(exercise_name: str) -> Optional[str]:
    params = {
        "part": "snippet",
        "q": f"{exercise_name} exercise tutorial short",
        "type": "video",
        "videoDuration": "short",
        "maxResults": 1,
        "key": API_KEY
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(YOUTUBE_API_URL, params=params)
        data = response.json()
        items = data.get("items", [])
        if items:
            video_id = items[0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={video_id}"
    return None