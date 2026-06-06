def test_allowed_hosts_include_app_host(settings):
    assert "plastic-hub.local" in settings.ALLOWED_HOSTS
