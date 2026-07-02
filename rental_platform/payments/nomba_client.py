import time
import requests
from django.conf import settings

# In-memory cache — stores the token and when it expires
# This lives in memory while the server is running
_token_cache = {
    'access_token': None,
    'expires_at': 0  # Unix timestamp of when the token expires
}

def get_access_token():
    # Check if we have a cached token that is still valid
    # We refresh 5 minutes early (300 seconds) to avoid expiry mid-request
    if _token_cache['access_token'] and time.time() < _token_cache['expires_at'] - 300:
        return _token_cache['access_token']

    # No valid token found — request a fresh one from Nomba
    response = requests.post(
        f"{settings.NOMBA_BASE_URL}/auth/token/issue",
        headers={
            'Content-Type': 'application/json',
            'accountId': settings.NOMBA_ACCOUNT_ID,
        },
        json={
            'grant_type': 'client_credentials',
            'client_id': settings.NOMBA_CLIENT_ID,
            'client_secret': settings.NOMBA_CLIENT_SECRET,
        }
    )

    result = response.json()

    # Nomba returns code '00' for success
    if result.get('code') != '00':
        raise Exception(f"Nomba authentication failed: {result}")

    # Save the token and set expiry to 60 minutes from now
    _token_cache['access_token'] = result['data']['access_token']
    _token_cache['expires_at'] = time.time() + 3600  # 60 minutes

    return _token_cache['access_token']


def nomba_post(endpoint, json_data):
    # Helper for making POST requests to Nomba with the right headers
    token = get_access_token()
    response = requests.post(
        f"{settings.NOMBA_BASE_URL}{endpoint}",
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'accountId': settings.NOMBA_ACCOUNT_ID,
        },
        json=json_data
    )
    return response.json()


def nomba_get(endpoint, params=None):
    # Helper for making GET requests to Nomba with the right headers
    token = get_access_token()
    response = requests.get(
        f"{settings.NOMBA_BASE_URL}{endpoint}",
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'accountId': settings.NOMBA_ACCOUNT_ID,
        },
        params=params
    )
    return response.json()