from routing.time_sensitive_classifier import classify_time_sensitivity


def test_improve_graphics_is_not_political_time_sensitive():
    result = classify_time_sensitivity("improve the graphics")
    assert result["is_time_sensitive"] is False
    assert result["category"] == "safe"


def test_improve_graphics_does_not_generate_browser_search_fallback():
    result = classify_time_sensitivity("i was saying to improve the graphics of the game we were creating")
    assert result["is_time_sensitive"] is False
    assert "political" not in result["reason"].lower()


def test_political_query_still_detected():
    result = classify_time_sensitivity("who is the cm of mp")
    assert result["is_time_sensitive"] is True
    assert result["category"] == "political"
