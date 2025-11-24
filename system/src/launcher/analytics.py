"""
Analytics module for Telegram Channel Reposter
Tracks posts, generations, views and user actions
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

# Analytics file path
ANALYTICS_FILE = os.path.join(os.environ.get("APPDATA", ""), "TelegramBotData", "data", "configs", "analytics.json")

class Analytics:
    """Analytics tracker for launcher actions"""
    
    def __init__(self):
        self.data = self._load_data()
    
    def _load_data(self) -> dict:
        """Load analytics data from file"""
        default_data = {
            "posts": {
                "total": 0,
                "by_date": {},
                "by_topic": {}
            },
            "generations": {
                "text": {"total": 0, "by_date": {}},
                "image": {"total": 0, "by_date": {}}
            },
            "edits": {
                "manual": {"total": 0, "by_date": {}},
                "auto": {"total": 0, "by_date": {}}
            },
            "views": {
                "total": 0,
                "by_date": {}
            },
            "sessions": {
                "total": 0,
                "total_time": 0,
                "by_date": {}
            },
            "models_used": {},
            "last_updated": None
        }
        
        try:
            if os.path.exists(ANALYTICS_FILE):
                with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults for missing keys
                    for key in default_data:
                        if key not in loaded:
                            loaded[key] = default_data[key]
                    return loaded
        except (json.JSONDecodeError, IOError):
            pass
        
        return default_data
    
    def _save_data(self):
        """Save analytics data to file"""
        try:
            self.data["last_updated"] = datetime.now().isoformat()
            os.makedirs(os.path.dirname(ANALYTICS_FILE), exist_ok=True)
            with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except (IOError, OSError):
            pass
    
    def _get_today(self) -> str:
        """Get today's date as string"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def track_post(self, topic: str = "default"):
        """Track a new post"""
        today = self._get_today()
        self.data["posts"]["total"] += 1
        self.data["posts"]["by_date"][today] = self.data["posts"]["by_date"].get(today, 0) + 1
        self.data["posts"]["by_topic"][topic] = self.data["posts"]["by_topic"].get(topic, 0) + 1
        self._save_data()
    
    def track_text_generation(self, model: str = "unknown"):
        """Track text generation"""
        today = self._get_today()
        self.data["generations"]["text"]["total"] += 1
        self.data["generations"]["text"]["by_date"][today] = \
            self.data["generations"]["text"]["by_date"].get(today, 0) + 1
        self.data["models_used"][model] = self.data["models_used"].get(model, 0) + 1
        self._save_data()
    
    def track_image_generation(self):
        """Track image generation"""
        today = self._get_today()
        self.data["generations"]["image"]["total"] += 1
        self.data["generations"]["image"]["by_date"][today] = \
            self.data["generations"]["image"]["by_date"].get(today, 0) + 1
        self._save_data()
    
    def track_manual_edit(self):
        """Track manual edit"""
        today = self._get_today()
        self.data["edits"]["manual"]["total"] += 1
        self.data["edits"]["manual"]["by_date"][today] = \
            self.data["edits"]["manual"]["by_date"].get(today, 0) + 1
        self._save_data()
    
    def track_view(self, count: int = 1):
        """Track views"""
        today = self._get_today()
        self.data["views"]["total"] += count
        self.data["views"]["by_date"][today] = self.data["views"]["by_date"].get(today, 0) + count
        self._save_data()
    
    def track_session(self, duration_seconds: int = 0):
        """Track session"""
        today = self._get_today()
        self.data["sessions"]["total"] += 1
        self.data["sessions"]["total_time"] += duration_seconds
        self.data["sessions"]["by_date"][today] = self.data["sessions"]["by_date"].get(today, 0) + 1
        self._save_data()
    
    def get_stats(self) -> dict:
        """Get all statistics"""
        return {
            "posts_total": self.data["posts"]["total"],
            "posts_today": self.data["posts"]["by_date"].get(self._get_today(), 0),
            "text_generations_total": self.data["generations"]["text"]["total"],
            "text_generations_today": self.data["generations"]["text"]["by_date"].get(self._get_today(), 0),
            "image_generations_total": self.data["generations"]["image"]["total"],
            "image_generations_today": self.data["generations"]["image"]["by_date"].get(self._get_today(), 0),
            "manual_edits_total": self.data["edits"]["manual"]["total"],
            "views_total": self.data["views"]["total"],
            "sessions_total": self.data["sessions"]["total"],
            "models_used": self.data["models_used"],
            "posts_by_topic": self.data["posts"]["by_topic"]
        }
    
    def get_chart_data(self, days: int = 7) -> dict:
        """Get data for charts (last N days)"""
        dates = []
        posts = []
        text_gens = []
        image_gens = []
        
        for i in range(days - 1, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            dates.append(date[-5:])  # MM-DD format
            posts.append(self.data["posts"]["by_date"].get(date, 0))
            text_gens.append(self.data["generations"]["text"]["by_date"].get(date, 0))
            image_gens.append(self.data["generations"]["image"]["by_date"].get(date, 0))
        
        return {
            "dates": dates,
            "posts": posts,
            "text_generations": text_gens,
            "image_generations": image_gens
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        self.data = {
            "posts": {"total": 0, "by_date": {}, "by_topic": {}},
            "generations": {
                "text": {"total": 0, "by_date": {}},
                "image": {"total": 0, "by_date": {}}
            },
            "edits": {
                "manual": {"total": 0, "by_date": {}},
                "auto": {"total": 0, "by_date": {}}
            },
            "views": {"total": 0, "by_date": {}},
            "sessions": {"total": 0, "total_time": 0, "by_date": {}},
            "models_used": {},
            "last_updated": None
        }
        self._save_data()


# Global analytics instance
_analytics = None

def get_analytics() -> Analytics:
    """Get global analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics

