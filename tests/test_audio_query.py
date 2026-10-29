"""详情 / 音频流 / 波形接口。"""

import os

import main


def test_detail_returns_full_payload(client, upload, make_wav):
    audio_id = upload(make_wav(seconds=30.0)).json()["id"]

    body = client.get(f"/api/audio/{audio_id}").json()

    assert body["id"] == audio_id
    assert body["duration"] > 0
    assert body["like_count"] == 0
    assert body["dislike_count"] == 0
    assert body["stream_url"] == f"/api/audio/stream/{audio_id}"
    assert body["waveform_url"] == f"/api/audio/{audio_id}/waveform"


def test_detail_404_for_unknown_id(client):
    response = client.get("/api/audio/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "音频不存在"


def test_stream_serves_uploaded_file(client, upload, make_wav):
    audio_id = upload(make_wav(seconds=2.0)).json()["id"]

    response = client.get(f"/api/audio/stream/{audio_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert len(response.content) > 0


def test_stream_404_for_unknown_id(client):
    assert client.get("/api/audio/stream/999999").status_code == 404


def test_stream_returns_500_when_file_vanished_from_disk(raw_client, upload, make_wav):
    """记录当前行为：数据库有记录但文件已不在磁盘时会 500。

    Vercel 的 /tmp 在实例回收后清空，线上就会走到这条路径。
    """
    audio_id = upload(make_wav(seconds=2.0)).json()["id"]
    for name in os.listdir(main.UPLOAD_DIR):
        os.remove(os.path.join(main.UPLOAD_DIR, name))

    assert raw_client.get(f"/api/audio/stream/{audio_id}").status_code == 500


def test_waveform_returns_bounded_point_list(client, upload, make_wav):
    audio_id = upload(make_wav(seconds=30.0)).json()["id"]

    body = client.get(f"/api/audio/{audio_id}/waveform").json()

    assert 0 < len(body["waveform"]) <= 200
    assert all(isinstance(v, (int, float)) for v in body["waveform"])
    assert body["duration"] > 0


def test_waveform_404_for_unknown_id(client):
    assert client.get("/api/audio/999999/waveform").status_code == 404


def test_waveform_returns_500_for_corrupt_file(raw_client, seed_audio, tmp_path):
    bad = tmp_path / "corrupt.wav"
    bad.write_bytes(b"not audio")
    audio_id = seed_audio(file_path=str(bad))

    response = raw_client.get(f"/api/audio/{audio_id}/waveform")

    assert response.status_code == 500
    assert response.json()["detail"] == "波形数据提取失败"


def test_health_check(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
