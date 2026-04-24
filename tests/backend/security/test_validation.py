import pytest
from backend.security.validation import validate_repository_url

def test_validate_https_allowed_host():
    # Should not raise for allowed host
    validate_repository_url('https://github.com/example/repo', ['github.com'])

def test_validate_invalid_scheme():
    with pytest.raises(ValueError):
        validate_repository_url('http://github.com/example/repo', ['github.com'])

def test_validate_disallowed_host():
    with pytest.raises(ValueError):
        validate_repository_url('https://gitlab.com/example/repo', ['github.com'])

def test_validate_path_traversal():
    with pytest.raises(ValueError):
        validate_repository_url('https://github.com/../evil', ['github.com'])
