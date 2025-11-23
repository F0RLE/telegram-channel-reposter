"""Basic tests that should always pass"""
import pytest


def test_basic_math():
    """Simple math test that should always pass"""
    assert 1 + 1 == 2
    assert 2 * 2 == 4
    assert 10 / 2 == 5


def test_string_operations():
    """Simple string test that should always pass"""
    text = "Hello World"
    assert len(text) == 11
    assert text.lower() == "hello world"
    assert text.upper() == "HELLO WORLD"


def test_list_operations():
    """Simple list test that should always pass"""
    my_list = [1, 2, 3]
    assert len(my_list) == 3
    assert sum(my_list) == 6
    assert 2 in my_list


def test_dict_operations():
    """Simple dict test that should always pass"""
    my_dict = {"key1": "value1", "key2": "value2"}
    assert len(my_dict) == 2
    assert "key1" in my_dict
    assert my_dict["key1"] == "value1"

