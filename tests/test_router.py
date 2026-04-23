from unittest.mock import patch

import main as app_main


def test_route_intent_audio_forces_analyze():
    assert app_main.route_intent("hello", True) == "analyze"


def test_route_intent_talk_from_brain():
    with patch.object(app_main, "ask_brain", return_value="talk"):
        assert app_main.route_intent("explain major thirds", False) == "talk"


def test_route_intent_demo_from_brain():
    with patch.object(app_main, "ask_brain", return_value="demo"):
        assert app_main.route_intent("sing that for me", False) == "demo"
