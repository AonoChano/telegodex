from security import detect_sensitive_content, sanitize_input


def test_sanitize_input_trims_and_limits_text():
    assert sanitize_input("  hello world  ", max_length=20) == "hello world"
    assert sanitize_input("abcdef", max_length=3) == "abc"


def test_security_public_api_does_not_export_dead_auth_manager():
    import security

    assert not hasattr(security, "AuthManager")


def test_detect_sensitive_content_reports_known_categories():
    found, category = detect_sensitive_content("请检查这个身份证号码")

    assert found is True
    assert category == "个人信息"
