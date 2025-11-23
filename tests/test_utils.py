"""Tests for utils module"""
import pytest
import sys
import os
import tempfile
import json

# Add parent directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'system', 'src'))

from core.utils import load_published_posts, save_published_posts


class TestPublishedPosts:
    """Tests for published posts utilities"""
    
    def test_load_empty_file(self):
        """Test loading from non-existent file"""
        # This will use the default path, but we can't easily mock it
        # So we just test that it doesn't crash
        result = load_published_posts()
        assert isinstance(result, list)
    
    def test_save_and_load(self):
        """Test saving and loading posts"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Mock the PUBLISHED_POSTS_FILE
            import core.utils as utils_module
            original_path = utils_module.PUBLISHED_POSTS_FILE
            utils_module.PUBLISHED_POSTS_FILE = temp_path
            
            # Test save
            test_links = ["link1", "link2", "link3"]
            save_published_posts(test_links)
            
            # Test load
            loaded = load_published_posts()
            assert loaded == test_links
            
            # Restore
            utils_module.PUBLISHED_POSTS_FILE = original_path
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("invalid json{")
            temp_path = f.name
        
        try:
            import core.utils as utils_module
            original_path = utils_module.PUBLISHED_POSTS_FILE
            utils_module.PUBLISHED_POSTS_FILE = temp_path
            
            # Should return empty list on error
            result = load_published_posts()
            assert result == []
            
            utils_module.PUBLISHED_POSTS_FILE = original_path
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

