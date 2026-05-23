import asyncio

from zero_env_proxy.providers import ProviderResponse, call_mock_provider


def test_mock_provider_returns_deterministic_completion():
    response = asyncio.run(
        call_mock_provider(
            method="POST",
            path="v1/chat/completions",
            headers={},
            query={},
            body=b'{"messages":[]}',
        )
    )

    assert isinstance(response, ProviderResponse)
    assert response.status_code == 200
    assert response.media_type == "application/json"
    assert response.body["provider"] == "mockai"
    assert "Zero-Env Proxy mock response" in response.body["message"]
