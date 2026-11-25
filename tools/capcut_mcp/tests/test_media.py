import subprocess

import pytest

from capcut_mcp.media import _image_size, kind_from_ext, probe
from tests.conftest import make_png


def test_kind_from_ext():
    assert kind_from_ext("a.MP4") == "video"
    assert kind_from_ext("a.jpeg") == "photo"
    assert kind_from_ext("a.m4a") == "audio"
    with pytest.raises(ValueError):
        kind_from_ext("a.txt")


def test_png_size(tmp_path):
    assert _image_size(make_png(tmp_path / "x.png", 33, 17)) == (33, 17)


def test_jpeg_webp_size_with_pillow(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    Image.new("RGB", (120, 80)).save(tmp_path / "x.jpg", quality=80)
    Image.new("RGB", (50, 70)).save(tmp_path / "x.webp")
    assert _image_size(tmp_path / "x.jpg") == (120, 80)
    assert _image_size(tmp_path / "x.webp") == (50, 70)


def test_probe_real_video_with_ffmpeg(tmp_path):
    imageio_ffmpeg = pytest.importorskip("imageio_ffmpeg")
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    out = tmp_path / "c.mp4"
    subprocess.run([exe, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
                    "-f", "lavfi", "-i", "sine=d=2", "-shortest", "-pix_fmt", "yuv420p", str(out)],
                   check=True)
    info = probe(out)
    assert info.kind == "video" and (info.width, info.height) == (320, 240)
    assert abs(info.duration - 2.0) < 0.15 and info.has_audio is True
