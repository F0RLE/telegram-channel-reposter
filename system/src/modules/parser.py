"""Telegram channel parser with HTML scraping and validation"""
import logging
import re
import asyncio
import aiohttp
import ssl
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from config.settings import TELEGRAM_CHANNELS, reload_channels
from core.utils import load_published_posts
from core.constants import (
    DEFAULT_MAX_POSTS_PER_CHANNEL,
    DEFAULT_MAX_AGE_HOURS,
    PARSER_TIMEOUT,
    PARSER_MAX_RETRIES,
    SSL_VERIFY_REMOTE
)
from core.exceptions import ParserError, ValidationError
from core.validators import validate_channel_name, sanitize_text

logger = logging.getLogger(__name__)

# ==========================================
# 1. HELPERS
# ==========================================

def _parse_datetime_iso(datetime_str: str) -> Optional[datetime]:
    """
    Parses ISO date from <time> tag.
    Converts everything to UTC for consistent comparison.
    
    Args:
        datetime_str: ISO format datetime string
        
    Returns:
        Parsed datetime object in UTC or None if parsing fails
    """
    if not datetime_str or not isinstance(datetime_str, str):
        return None
    try:
        # Fix 'Z' suffix for older python versions
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, AttributeError) as e:
        logger.debug(f"Failed to parse datetime '{datetime_str}': {e}")
        return None

def _create_ssl_context(url: str) -> ssl.SSLContext:
    """
    Creates SSL context with appropriate verification settings.
    
    WARNING: SSL verification is disabled only for localhost connections.
    For remote connections (t.me), verification is enabled by default.
    
    Args:
        url: URL to determine SSL verification policy
        
    Returns:
        Configured SSL context
    """
    parsed = urlparse(url)
    is_localhost = parsed.hostname in ('127.0.0.1', 'localhost', '::1')
    
    ssl_context = ssl.create_default_context()
    
    # Only disable verification for localhost (safe for local services)
    # For remote connections, always verify certificates
    if is_localhost:
        logger.debug(f"SSL verification disabled for localhost: {url}")
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    else:
        # For t.me and other remote connections, verify certificates
        ssl_context.check_hostname = SSL_VERIFY_REMOTE
        ssl_context.verify_mode = ssl.CERT_REQUIRED if SSL_VERIFY_REMOTE else ssl.CERT_NONE
    
    return ssl_context


async def _fetch_channel_html(
    session: aiohttp.ClientSession, 
    channel_name: str, 
    max_retries: int = PARSER_MAX_RETRIES
) -> Optional[str]:
    """
    Downloads HTML page of a public Telegram channel with retry mechanism and rate limiting.
    
    Args:
        session: aiohttp client session
        channel_name: Telegram channel name (without @)
        max_retries: Maximum number of retry attempts
        
    Returns:
        HTML content string or None on error
        
    Raises:
        ValidationError: If channel name is invalid
        ParserError: If parsing fails after retries
    """
    # Validate channel name
    if not validate_channel_name(channel_name):
        raise ValidationError(f"Invalid channel name format: {channel_name}")
    
    from core.error_handler import retry_with_backoff, RetryConfig, ErrorHandler
    from launcher.core.rate_limiter import parser_rate_limiter
    from core.constants import DEFAULT_RETRY_INITIAL_DELAY, DEFAULT_RETRY_MAX_DELAY
    
    # Apply rate limiting
    await parser_rate_limiter.acquire(f"parser_{channel_name}")
    
    url = f"https://t.me/s/{channel_name}"
    
    retry_config = RetryConfig(
        max_attempts=max_retries,
        initial_delay=DEFAULT_RETRY_INITIAL_DELAY,
        max_delay=DEFAULT_RETRY_MAX_DELAY,
        retryable_exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
    )
    
    @retry_with_backoff(config=retry_config)
    async def _make_request():
        async with session.get(
            url, 
            timeout=aiohttp.ClientTimeout(total=PARSER_TIMEOUT),
            ssl=False  # SSL is handled by connector
        ) as response:
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
        # Return None instead of raising to allow graceful degradation
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
    
    Args:
        html: HTML content to parse
        channel_name: Name of the channel being parsed
        max_per_channel: Maximum number of posts to extract
        published_links: List of already published links to skip
        min_datetime: Minimum datetime for posts (filter old posts)
        
    Returns:
        List of parsed post dictionaries
    """
    if not html or not isinstance(html, str):
        logger.warning(f"Empty or invalid HTML for channel {channel_name}")
        return []
    
    found_posts = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        logger.error(f"Failed to parse HTML for {channel_name}: {e}")
        return []
    
    # Find all message blocks
    message_blocks = soup.find_all('div', class_='tgme_widget_message', limit=max_per_channel + 5)

    for block in message_blocks:
        try:
            # 1. Extract Link
            link_tag = block.find('a', class_='tgme_widget_message_date')
            post_link = link_tag.get('href') if link_tag else None
            if not post_link or not isinstance(post_link, str):
                continue

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
            
            # Sanitize text
            post_text = sanitize_text(post_text)

            # 4. Extract Media (Photos/Video Thumbs)
            media_urls = []
            
            # Telegram uses 'background-image: url(...)' for preview images
            # We regex search in 'style' attributes
            media_tags = block.find_all('a', class_=['tgme_widget_message_photo_wrap', 'tgme_widget_message_video_thumb'])
            
            for tag in media_tags:
                style = tag.get('style', '')
                if not isinstance(style, str):
                    continue
                # Regex to find url('...')
                match = re.search(r"url\('?(.*?)'?\)", style)
                if match: 
                    url = match.group(1).strip()
                    if url and url.startswith('http'):
                        media_urls.append(url)

            has_media = bool(media_urls)
            
            # 5. Filter Junk
            # Skip empty posts (no text, no media)
            if not post_text and not has_media:
                continue
            
            # Skip already published
            if post_link in published_links:
                continue

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
        except Exception as e:
            logger.debug(f"Error parsing message block in {channel_name}: {e}")
            continue
            
    return found_posts

# ==========================================
# 3. AGGREGATOR
# ==========================================

async def aggregate_topic_posts(
    topic_key: str, 
    max_per_channel: int = DEFAULT_MAX_POSTS_PER_CHANNEL, 
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS
) -> List[Dict[str, Any]]:
    """
    Main function. Scrapes all channels in the topic concurrently.
    
    Args:
        topic_key: Topic key to aggregate posts for
        max_per_channel: Maximum number of posts per channel
        max_age_hours: Maximum age of posts in hours
        
    Returns:
        List of aggregated post dictionaries, sorted by date (newest first)
        
    Raises:
        ValidationError: If topic_key is invalid
        ParserError: If parsing fails
    """
    if not topic_key or not isinstance(topic_key, str):
        raise ValidationError(f"Invalid topic_key: {topic_key}")
    
    # Перезагружаем каналы для актуальности
    reload_channels()
    channels = TELEGRAM_CHANNELS.get(topic_key, [])
    if not channels:
        logger.info(f"No channels found for topic: {topic_key}")
        return []

    # Validate channel names
    valid_channels = []
    for ch in channels:
        if validate_channel_name(ch):
            valid_channels.append(ch)
        else:
            logger.warning(f"Invalid channel name skipped: {ch}")
    
    if not valid_channels:
        logger.warning(f"No valid channels for topic: {topic_key}")
        return []

    # Load exclude list
    published_links = load_published_posts()
    min_datetime = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    
    aggregated = []

    # Create SSL context with proper verification
    # For t.me (remote), SSL verification is enabled
    # For localhost, verification is disabled (safe for local services)
    telegram_url = "https://t.me/s/test"  # Template URL for SSL context
    ssl_context = _create_ssl_context(telegram_url)
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            # 1. Parallel Download
            tasks = []
            for ch in valid_channels:
                tasks.append(_fetch_channel_html(session, ch))
            
            # Use return_exceptions to handle individual failures gracefully
            htmls = await asyncio.gather(*tasks, return_exceptions=True)

            # 2. Process Results
            for i, result in enumerate(htmls):
                if isinstance(result, Exception):
                    logger.error(f"Failed to fetch channel {valid_channels[i]}: {result}")
                    continue
                
                if result:  # result is HTML string
                    try:
                        posts = await _parse_channel_content(
                            result, valid_channels[i], max_per_channel, published_links, min_datetime
                        )
                        aggregated.extend(posts)
                    except Exception as e:
                        logger.error(f"Failed to parse content for {valid_channels[i]}: {e}")
                        continue
    except Exception as e:
        logger.error(f"Error in aggregate_topic_posts: {e}")
        raise ParserError(f"Failed to aggregate posts for topic {topic_key}: {str(e)}", context=str(e))

    # 3. Sort by Date (Newest first)
    aggregated.sort(
        key=lambda x: _parse_datetime_iso(x.get('timestamp')) or datetime.min.replace(tzinfo=timezone.utc), 
        reverse=True
    )

    logger.info(f"Aggregated {len(aggregated)} posts for topic {topic_key}")
    return aggregated[:100]  # Limit to 100 posts