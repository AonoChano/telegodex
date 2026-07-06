from security import sanitize_input


def test_sanitize_input_trims_and_limits_text():
    assert sanitize_input("  hello world  ", max_length=20) == "hello world"
    assert sanitize_input("abcdef", max_length=3) == "abc"


def test_security_public_api_does_not_export_dead_auth_manager():
    import security

    assert not hasattr(security, "AuthManager")


def test_security_public_api_does_not_export_sensitive_content_filter():
    import security

    assert not hasattr(security, "detect_sensitive_content")
