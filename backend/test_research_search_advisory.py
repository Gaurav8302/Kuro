import os

os.environ['DISABLE_MEMORY_INIT'] = '1'

from memory.chat_manager_v2 import _strip_redundant_search_warning


def test_strip_redundant_search_warning_removes_browser_search_advice():
    response = (
        "The United Kingdom does not have a president. It has a monarch as head of state "
        "and a prime minister as head of government.\n\n"
        "My knowledge may be outdated on this topic. You can enable browser search for the latest information."
    )

    cleaned = _strip_redundant_search_warning(response)

    assert "The United Kingdom does not have a president." in cleaned
    assert "enable browser search" not in cleaned.lower()
    assert "knowledge may be outdated" not in cleaned.lower()


def test_strip_redundant_search_warning_keeps_normal_answer_unchanged():
    response = "Yesterday in Indore it was mostly sunny with a high near 36C and no rain reported."

    cleaned = _strip_redundant_search_warning(response)

    assert cleaned == response