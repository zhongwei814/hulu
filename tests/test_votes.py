"""点赞 / 点踩接口。"""

import pytest

IP_A = {"X-Forwarded-For": "10.0.0.1"}
IP_B = {"X-Forwarded-For": "10.0.0.2"}


@pytest.fixture
def audio_id(seed_audio):
    return seed_audio()


# ---- 点赞 ----

def test_first_like_increments_count(client, audio_id):
    body = client.post(f"/api/audio/{audio_id}/like", headers=IP_A).json()
    assert body["like_count"] == 1


def test_duplicate_like_from_same_ip_is_ignored(client, audio_id):
    client.post(f"/api/audio/{audio_id}/like", headers=IP_A)

    body = client.post(f"/api/audio/{audio_id}/like", headers=IP_A).json()

    assert body["already_liked"] is True
    assert client.get(f"/api/audio/{audio_id}").json()["like_count"] == 1


def test_like_from_different_ip_counts_separately(client, audio_id):
    client.post(f"/api/audio/{audio_id}/like", headers=IP_A)

    body = client.post(f"/api/audio/{audio_id}/like", headers=IP_B).json()

    assert body["like_count"] == 2


def test_like_404_for_unknown_audio(client):
    assert client.post("/api/audio/999999/like").status_code == 404


# ---- 点踩 ----

def test_first_dislike_increments_count(client, audio_id):
    body = client.post(f"/api/audio/{audio_id}/dislike", headers=IP_A).json()
    assert body["dislike_count"] == 1


def test_duplicate_dislike_from_same_ip_is_ignored(client, audio_id):
    client.post(f"/api/audio/{audio_id}/dislike", headers=IP_A)

    body = client.post(f"/api/audio/{audio_id}/dislike", headers=IP_A).json()

    assert body["already_disliked"] is True
    assert client.get(f"/api/audio/{audio_id}").json()["dislike_count"] == 1


def test_dislike_404_for_unknown_audio(client):
    assert client.post("/api/audio/999999/dislike").status_code == 404


# ---- 两者互不影响 ----

def test_like_and_dislike_are_independent(client, audio_id):
    client.post(f"/api/audio/{audio_id}/like", headers=IP_A)
    client.post(f"/api/audio/{audio_id}/dislike", headers=IP_A)

    body = client.get(f"/api/audio/{audio_id}").json()
    assert body["like_count"] == 1
    assert body["dislike_count"] == 1
