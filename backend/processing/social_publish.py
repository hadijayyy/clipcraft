"""Direct social media publishing — TikTok, YouTube, Instagram"""

import os
import json
import subprocess
import requests

# API credentials (set via environment variables)
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_ACCESS_TOKEN = os.getenv("YOUTUBE_ACCESS_TOKEN", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ID = os.getenv("INSTAGRAM_BUSINESS_ID", "")


def publish_to_tiktok(video_path: str, title: str, description: str, tags: list) -> dict:
    """Publish video to TikTok via Content Posting API.
    
    Flow: Upload video → Initialize publish → Check status
    Reference: https://developers.tiktok.com/doc/content-posting-api
    """
    if not TIKTOK_ACCESS_TOKEN:
        return {
            "status": "manual_upload_required",
            "message": "TikTok API token not configured. Download the clip and upload manually.",
            "download_url": video_path,
            "instructions": {
                "step1": "Open TikTok app",
                "step2": "Tap + to create new post",
                "step3": "Select the downloaded video",
                "step4": f"Add caption: {title} {' '.join(['#' + t for t in tags])}" if tags else f"Add caption: {title}",
                "step5": "Post!"
            }
        }
    
    # TikTok Content Posting API flow
    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Initialize upload
    init_resp = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title": title,
                "description": f"{description} {' '.join(['#' + t for t in tags])}".strip()
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": os.path.getsize(video_path)
            }
        }
    )
    init_resp.raise_for_status()
    init_data = init_resp.json().get("data", {})
    
    upload_url = init_data.get("upload_url")
    publish_id = init_data.get("publish_id")
    
    if not upload_url:
        raise RuntimeError("Failed to get TikTok upload URL")
    
    # Step 2: Upload video file
    with open(video_path, "rb") as f:
        upload_resp = requests.put(
            upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{os.path.getsize(video_path)-1}/{os.path.getsize(video_path)}"
            },
            data=f
        )
        upload_resp.raise_for_status()
    
    return {
        "status": "uploaded",
        "platform": "tiktok",
        "publish_id": publish_id,
        "message": "Video uploaded to TikTok. Processing may take a few minutes."
    }


def publish_to_youtube(video_path: str, title: str, description: str, tags: list) -> dict:
    """Publish video to YouTube via YouTube Data API v3.
    
    Reference: https://developers.google.com/youtube/v3/docs/videos/insert
    """
    if not YOUTUBE_ACCESS_TOKEN:
        return {
            "status": "manual_upload_required",
            "message": "YouTube API token not configured. Download the clip and upload manually.",
            "download_url": video_path,
            "instructions": {
                "step1": "Go to studio.youtube.com",
                "step2": "Click Create → Upload video",
                "step3": "Select the downloaded video",
                "step4": f"Title: {title}",
                "step5": f"Description: {description}",
                "step6": f"Tags: {', '.join(tags)}" if tags else "",
                "step7": "Set visibility and publish"
            }
        }
    
    # YouTube resumable upload
    headers = {
        "Authorization": f"Bearer {YOUTUBE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Initialize resumable upload
    init_resp = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers=headers,
        json={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": "private"  # Start as private, user can publish
            }
        }
    )
    init_resp.raise_for_status()
    upload_url = init_resp.headers.get("Location")
    
    if not upload_url:
        raise RuntimeError("Failed to get YouTube upload URL")
    
    # Step 2: Upload video
    with open(video_path, "rb") as f:
        upload_resp = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {YOUTUBE_ACCESS_TOKEN}",
                "Content-Type": "video/mp4"
            },
            data=f
        )
        upload_resp.raise_for_status()
    
    video_data = upload_resp.json()
    
    return {
        "status": "uploaded",
        "platform": "youtube",
        "video_id": video_data.get("id"),
        "message": "Video uploaded to YouTube as private. Go to Studio to publish."
    }


def publish_to_instagram(video_path: str, title: str, description: str, tags: list) -> dict:
    """Publish video to Instagram via Instagram Graph API.
    
    Flow: Create media container → Publish
    Reference: https://developers.facebook.com/docs/instagram-api/ig-reels
    """
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ID:
        return {
            "status": "manual_upload_required",
            "message": "Instagram API not configured. Download the clip and upload manually.",
            "download_url": video_path,
            "instructions": {
                "step1": "Open Instagram app",
                "step2": "Tap + → Reel",
                "step3": "Select the downloaded video",
                "step4": f"Caption: {title} {' '.join(['#' + t for t in tags])}" if tags else f"Caption: {title}",
                "step5": "Share to Reels"
            }
        }
    
    # Instagram Reels API flow
    # Step 1: Create media container
    container_resp = requests.post(
        f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ID}/media",
        data={
            "media_type": "REELS",
            "video_url": video_path,  # Must be a public URL
            "caption": f"{title}\n\n{description} {' '.join(['#' + t for t in tags])}".strip(),
            "access_token": INSTAGRAM_ACCESS_TOKEN
        }
    )
    container_resp.raise_for_status()
    container_id = container_resp.json().get("id")
    
    if not container_id:
        raise RuntimeError("Failed to create Instagram media container")
    
    # Step 2: Wait for processing and publish
    import time
    for _ in range(30):  # Wait up to 5 minutes
        status_resp = requests.get(
            f"https://graph.facebook.com/v18.0/{container_id}",
            params={
                "fields": "status_code",
                "access_token": INSTAGRAM_ACCESS_TOKEN
            }
        )
        status = status_resp.json().get("status_code")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            raise RuntimeError("Instagram media processing failed")
        time.sleep(10)
    
    # Step 3: Publish
    publish_resp = requests.post(
        f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ID}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN
        }
    )
    publish_resp.raise_for_status()
    
    return {
        "status": "published",
        "platform": "instagram",
        "media_id": publish_resp.json().get("id"),
        "message": "Video published to Instagram Reels!"
    }
