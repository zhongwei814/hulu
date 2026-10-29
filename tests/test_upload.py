"""上传接口 /api/audio/upload。"""

import os

import pytest

import main


def _uploaded_files():
    return sorted(os.listdir(main.UPLOAD_DIR))


# ---- 正常路径 ----

def test_upload_succeeds_and_returns_id(upload, make_wav):
    response = upload(make_wav(seconds=5.0))

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["nickname"]
    assert "上传成功" in body["message"]


def test_upload_generates_nickname_when_blank(upload, make_wav):
    body = upload(make_wav(seconds=5.0), nickname="   ").json()
    assert body["nickname"].strip()


def test_upload_keeps_custom_nickname_trimmed(upload, make_wav):
    body = upload(make_wav(seconds=5.0), nickname="  呼噜之王  ").json()
    assert body["nickname"] == "呼噜之王"


def test_upload_persists_file_on_disk(upload, make_wav):
    upload(make_wav(seconds=5.0))
    assert len(_uploaded_files()) == 1


def test_upload_runs_scoring_in_background(client, upload, make_wav):
    audio_id = upload(make_wav(seconds=30.0)).json()["id"]

    detail = client.get(f"/api/audio/{audio_id}").json()

    assert detail["score"] is not None
    assert set(detail["score_detail"]) == {
        "loudness_peak",
        "freq_richness",
        "stability",
        "dynamic_range",
        "duration_score",
    }


def test_upload_accepts_different_supported_extensions(client, tmp_path):
    for ext in (".mp3", ".wav", ".ogg", ".webm"):
        path = tmp_path / f"clip{ext}"
        path.write_bytes(b"\x00" * 64)
        with open(path, "rb") as f:
            response = client.post(
                "/api/audio/upload", files={"file": (f"clip{ext}", f, "audio/mpeg")}
            )
        # 扩展名校验应通过，失败只可能发生在解析阶段（400），而不是格式不支持
        assert response.status_code == 400
        assert "不支持的格式" not in response.json()["detail"]


# ---- 拒绝路径 ----

@pytest.mark.parametrize("filename", ["note.txt", "clip.mp4", "noext", "clip.exe"])
def test_upload_rejects_unsupported_extension(client, make_wav, filename):
    path = make_wav(seconds=1.0)
    with open(path, "rb") as f:
        response = client.post(
            "/api/audio/upload", files={"file": (filename, f, "application/octet-stream")}
        )

    assert response.status_code == 400
    assert "不支持的格式" in response.json()["detail"]
    assert _uploaded_files() == []


def test_upload_rejects_file_over_10mb(client, tmp_path):
    big = tmp_path / "big.wav"
    big.write_bytes(b"\x00" * (11 * 1024 * 1024))

    with open(big, "rb") as f:
        response = client.post("/api/audio/upload", files={"file": ("big.wav", f, "audio/wav")})

    assert response.status_code == 400
    assert "10MB" in response.json()["detail"]
    assert _uploaded_files() == []


def test_upload_rejects_audio_over_180_seconds(upload, make_wav):
    response = upload(make_wav(seconds=200.0))

    assert response.status_code == 400
    assert "时长" in response.json()["detail"]
    assert _uploaded_files() == []


def test_upload_rejects_corrupt_audio_and_cleans_up(upload, tmp_path):
    bad = tmp_path / "corrupt.wav"
    bad.write_bytes(b"this is not a real audio file")

    response = upload(bad)

    assert response.status_code == 400
    assert "无法解析" in response.json()["detail"]
    assert _uploaded_files() == []


def test_upload_requires_file_field(client):
    response = client.post("/api/audio/upload", data={"nickname": "x"})
    assert response.status_code == 422


# ---- IP 限流 ----

def test_upload_allows_three_per_ip_then_blocks(upload, make_wav):
    path = make_wav(seconds=1.0)

    for i in range(3):
        assert upload(path, ip="10.0.0.7").status_code == 200, f"第 {i + 1} 次应放行"

    blocked = upload(path, ip="10.0.0.7")
    assert blocked.status_code == 429
    assert "频繁" in blocked.json()["detail"]


def test_upload_rate_limit_is_per_ip(upload, make_wav):
    path = make_wav(seconds=1.0)

    for _ in range(3):
        upload(path, ip="10.0.0.7")

    assert upload(path, ip="10.0.0.8").status_code == 200


def test_upload_rate_limit_trusts_x_forwarded_for(upload, make_wav):
    """记录当前行为：X-Forwarded-For 可被客户端伪造，限流形同虚设。

    生产环境需要改为只信任反向代理注入的可信 IP，否则防刷可被轻易绕过。
    """
    path = make_wav(seconds=1.0)

    for i in range(3):
        upload(path, ip="10.0.0.7")

    assert upload(path, ip="1.2.3.4").status_code == 200
