"""排行榜接口。"""

from datetime import datetime, timedelta, timezone

import pytest


def _ago(**kwargs):
    return datetime.now(timezone.utc) - timedelta(**kwargs)


# ---- 排序与截断 ----

def test_likes_leaderboard_sorted_by_like_count_desc(client, seed_audio):
    seed_audio(nickname="low", like_count=1)
    seed_audio(nickname="high", like_count=9)
    seed_audio(nickname="mid", like_count=5)

    body = client.get("/api/leaderboard/likes").json()

    assert [item["nickname"] for item in body] == ["high", "mid", "low"]


def test_likes_leaderboard_is_capped_at_ten(client, seed_audio):
    for i in range(15):
        seed_audio(nickname=f"user{i}", like_count=i)

    body = client.get("/api/leaderboard/likes").json()

    assert len(body) == 10
    assert body[0]["like_count"] == 14


def test_scores_leaderboard_excludes_unscored_audio(client, seed_audio):
    seed_audio(nickname="scored", score=88.0)
    seed_audio(nickname="pending", score=None)

    body = client.get("/api/leaderboard/scores").json()

    assert [item["nickname"] for item in body] == ["scored"]


def test_scores_leaderboard_sorted_desc(client, seed_audio):
    seed_audio(nickname="a", score=40.0)
    seed_audio(nickname="b", score=95.0)
    seed_audio(nickname="c", score=70.0)

    body = client.get("/api/leaderboard/scores").json()

    assert [item["nickname"] for item in body] == ["b", "c", "a"]


def test_empty_leaderboards_return_empty_list(client):
    assert client.get("/api/leaderboard/likes").json() == []
    assert client.get("/api/leaderboard/scores").json() == []


# ---- range 过滤 ----

@pytest.mark.parametrize("endpoint", ["/api/leaderboard/likes", "/api/leaderboard/scores"])
def test_invalid_range_is_rejected(client, endpoint):
    response = client.get(endpoint, params={"range": "month"})

    assert response.status_code == 400
    assert "all/week/today" in response.json()["detail"]


@pytest.mark.parametrize("range_value", ["all", "week", "today"])
def test_valid_range_values_are_accepted(client, range_value):
    assert client.get("/api/leaderboard/likes", params={"range": range_value}).status_code == 200


def test_week_range_excludes_older_uploads(client, seed_audio):
    seed_audio(nickname="fresh", like_count=5, created_at=_ago(days=1))
    seed_audio(nickname="stale", like_count=9, created_at=_ago(days=10))

    body = client.get("/api/leaderboard/likes", params={"range": "week"}).json()

    assert [item["nickname"] for item in body] == ["fresh"]


def test_today_range_excludes_previous_days(client, seed_audio):
    seed_audio(nickname="today", like_count=5, created_at=_ago(minutes=1))
    seed_audio(nickname="yesterday", like_count=9, created_at=_ago(days=1, hours=1))

    body = client.get("/api/leaderboard/likes", params={"range": "today"}).json()

    assert [item["nickname"] for item in body] == ["today"]


def test_all_range_includes_everything(client, seed_audio):
    seed_audio(nickname="fresh", like_count=5, created_at=_ago(days=1))
    seed_audio(nickname="stale", like_count=9, created_at=_ago(days=400))

    body = client.get("/api/leaderboard/likes", params={"range": "all"}).json()

    assert {item["nickname"] for item in body} == {"fresh", "stale"}


def test_range_filter_applies_to_scores_leaderboard(client, seed_audio):
    seed_audio(nickname="fresh", score=50.0, created_at=_ago(days=1))
    seed_audio(nickname="stale", score=99.0, created_at=_ago(days=30))

    body = client.get("/api/leaderboard/scores", params={"range": "week"}).json()

    assert [item["nickname"] for item in body] == ["fresh"]
