import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts import generate_blog_post as blog


def test_missing_optional_files_use_honest_fallbacks(tmp_path, monkeypatch):
    monkeypatch.setattr(blog, "OVERALL_STATS_FILE", tmp_path / "missing_overall.json")
    release_dir = tmp_path / "output" / "2026-05-14"
    posts_dir = tmp_path / "_posts"
    release_dir.mkdir(parents=True)

    post_path = blog.generate_blog_post(
        release_date="2026-05-14",
        generated_at=datetime(2026, 5, 14, tzinfo=timezone.utc),
        posts_dir=posts_dir,
        release_dir=release_dir,
    )

    content = post_path.read_text()
    assert "not recorded" in content
    assert "Chart data was unavailable" in content
    assert "daily-chart-data" not in content
    assert "1240" not in content
    assert "99.8" not in content


def test_zero_new_word_day_is_distinct_from_missing_metrics(tmp_path, monkeypatch):
    overall = tmp_path / "overall_stats.json"
    overall.write_text(json.dumps({"last_updated": "2026-05-24", "total_valid_words": 10}))
    monkeypatch.setattr(blog, "OVERALL_STATS_FILE", overall)
    release_dir = tmp_path / "output" / "2026-05-24"
    posts_dir = tmp_path / "_posts"
    release_dir.mkdir(parents=True)
    (release_dir / "update_stats.json").write_text(json.dumps({"new_words": [], "promoted_words": []}))

    post_path = blog.generate_blog_post(
        release_date="2026-05-24",
        generated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        posts_dir=posts_dir,
        release_dir=release_dir,
    )

    content = post_path.read_text()
    assert "**Total words added today:** 0" in content
    assert "**New words discovered today:** 0" in content
    assert "**Words promoted from invalid list:** 0" in content
    assert "**Total valid words now:** **10**" in content


def test_valid_chart_data_is_embedded_safely(tmp_path, monkeypatch):
    monkeypatch.setattr(blog, "OVERALL_STATS_FILE", tmp_path / "missing_overall.json")
    release_dir = tmp_path / "output" / "2026-05-24"
    posts_dir = tmp_path / "_posts"
    release_dir.mkdir(parents=True)
    (release_dir / "word_length_distribution.csv").write_text("word_length,count\n2,1\n3,2\n")
    (release_dir / "starting_letter_distribution.csv").write_text("starting_letter,count\na,1\nb,2\n")

    post_path = blog.generate_blog_post(
        release_date="2026-05-24",
        generated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        posts_dir=posts_dir,
        release_dir=release_dir,
    )

    content = post_path.read_text()
    assert "daily-chart-data" in content
    assert "daily-update-charts.js" in content
    assert "Chart data was unavailable" not in content


def test_malformed_chart_data_is_omitted(tmp_path, monkeypatch):
    monkeypatch.setattr(blog, "OVERALL_STATS_FILE", tmp_path / "missing_overall.json")
    release_dir = tmp_path / "output" / "2026-05-24"
    posts_dir = tmp_path / "_posts"
    release_dir.mkdir(parents=True)
    (release_dir / "word_length_distribution.csv").write_text("word_length,count\nbad,1\n")
    (release_dir / "starting_letter_distribution.csv").write_text("starting_letter,count\na,1\n")

    post_path = blog.generate_blog_post(
        release_date="2026-05-24",
        generated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        posts_dir=posts_dir,
        release_dir=release_dir,
    )

    content = post_path.read_text()
    assert "Chart data was unavailable" in content
    assert "daily-chart-data" not in content
