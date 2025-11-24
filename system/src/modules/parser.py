import logging
import re
import asyncio
import aiohttp
import ssl
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

from config.settings import TELEGRAM_CHANNELS, reload_channels
from core.utils import load_published_posts

logger = logging.getLogger(__name__)

# ==========================================
# 1. HELPERS
# ==========================================

def _parse_datetime_iso(datetime_str: str) -> Optional[datetime]:
    """
    Parses ISO date from <time> tag.
    Converts everything to UTC for consistent comparison.
    """
    if not datetime_str:
        return None
    try:
        # Fix 'Z' suffix for older python versions
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None

async def _fetch_channel_html(session: aiohttp.ClientSession, channel_name: str, max_retries: int = 3) -> Optional[str]:
    """
    Downloads HTML page of a public Telegram channel with retry mechanism and rate limiting.
    
    Args:
        session: aiohttp client session
        channel_name: Telegram channel name (without @)
        max_retries: Maximum number of retry attempts
        
    Returns:
        HTML content string or None on error
    """
    from core.error_handler import retry_with_backoff, RetryConfig, ErrorHandler
    from launcher.core.rate_limiter import parser_rate_limiter
    
    # Apply rate limiting
    await parser_rate_limiter.acquire(f"parser_{channel_name}")
    
    url = f"https://t.me/s/{channel_name}"
    
    retry_config = RetryConfig(
        max_attempts=max_retries,
        initial_delay=1.0,
        max_delay=10.0,
        retryable_exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
    )
    
    @retry_with_backoff(config=retry_config)
    async def _make_request():
        # Use ssl=False since SSL context is already configured in connector
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as response:
            if response.status == 200:
                return await response.text()
            elif response.status == 429:
                # Rate limit - wait longer
                await asyncio.sleep(5)
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Rate limit exceeded"
                )
            else:
                error_msg = f"Канал {channel_name} вернул статус {response.status}"
                logger.warning(f"⚠️ {error_msg}")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_msg
                )
    
    try:
        return await _make_request()
    except Exception as e:
        error_msg = ErrorHandler.handle_api_error(e, f"Ошибка соединения с {channel_name}")
        logger.error(f"❌ {error_msg}")
        return None

# ==========================================
# 2. PARSING LOGIC
# ==========================================

async def _parse_channel_content(
    html: str,
    channel_name: str,
    max_per_channel: int,
    published_links: List[str],
    min_datetime: datetime
) -> List[Dict[str, Any]]:
    """
    Extracts posts from raw HTML using BeautifulSoup.
    """
    found_posts = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all message blocks
    message_blocks = soup.find_all('div', class_='tgme_widget_message', limit=max_per_channel + 5)

    for block in message_blocks:
        # 1. Extract Link
        link_tag = block.find('a', class_='tgme_widget_message_date')
        post_link = link_tag.get('href') if link_tag else None
        if not post_link: continue

        # 2. Check Date
        time_tag = block.find('time')
        timestamp_str = time_tag.get('datetime') if time_tag else None
        post_dt = _parse_datetime_iso(timestamp_str)
        
        # Skip old posts or invalid dates
        if post_dt is None or post_dt < min_datetime:
            continue

        # 3. Extract Text
        text_block = block.find('div', class_='tgme_widget_message_text')
        post_text = ""
        if text_block:
            # Replace <br> with newlines
            for br in text_block.find_all("br"):
                br.replace_with("\n")
            post_text = text_block.get_text("\n", strip=True)

        # 4. Extract Media (Photos/Video Thumbs)
        media_urls = []
        
        # Telegram uses 'background-image: url(...)' for preview images
        # We regex search in 'style' attributes
        media_tags = block.find_all('a', class_=['tgme_widget_message_photo_wrap', 'tgme_widget_message_video_thumb'])
        
        for tag in media_tags:
            style = tag.get('style', '')
            # Regex to find url('...')
            match = re.search(r"url\('?(.*?)'?\)", style)
            if match: 
                media_urls.append(match.group(1))

        has_media = bool(media_urls)
        
        # 5. Filter Junk
        # Skip empty posts (no text, no media)
        if not post_text and not has_media: continue
        
        # Skip already published
        if post_link in published_links: continue

        found_posts.append({
            'channel': channel_name,
            'text': post_text,
            'link': post_link,
            'timestamp': timestamp_str,
            'has_media': has_media,
            'media_urls': media_urls,
            # Note: Parser cannot distinguish video file from photo, 
            # so everything comes as 'photo' (thumbnail) for safety.
            'media_type': 'photo' if has_media else None 
        })

        if len(found_posts) >= max_per_channel:
            break
            
    return found_posts

# ==========================================
# 3. AGGREGATOR
# ==========================================

async def aggregate_topic_posts(
    topic_key: str, 
    max_per_channel: int = 5, 
    max_age_hours: int = 48
) -> List[Dict[str, Any]]:
    """
    Main function. Scrapes all channels in the topic concurrently.
    """
    # Перезагружаем каналы для актуальности
    reload_channels()
    channels = TELEGRAM_CHANNELS.get(topic_key, [])
    if not channels:
        return []

    # Load exclude list
    published_links = load_published_posts()
    min_datetime = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    
    aggregated = []

    # Connector with SSL configuration that allows self-signed certificates
    # This is needed when corporate proxy or antivirus injects self-signed certificates
    import ssl
    ssl_context = ssl.create_default_context()
    # Disable certificate verification to allow self-signed certificates
    # This is safe for public Telegram channels (t.me) as we're only reading public HTML
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
        # 1. Parallel Download
        tasks = []
        for ch in channels:
            tasks.append(_fetch_channel_html(session, ch))
        
        htmls = await asyncio.gather(*tasks)

        # 2. Process Results
        for i, html in enumerate(htmls):
            if html:
                posts = await _parse_channel_content(
                    html, channels[i], max_per_channel, published_links, min_datetime
                )
                aggregated.extend(posts)

    # 3. Sort by Date (Newest first)
    aggregated.sort(
        key=lambda x: _parse_datetime_iso(x.get('timestamp')) or datetime.min.replace(tzinfo=timezone.utc), 
        reverse=True
    )

    return aggregated[:100]