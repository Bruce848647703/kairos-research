"""离线测试：校验 kairos-research 文档仓库的完整性与可溯源性。

不联网、不依赖兄弟仓库（兄弟仓库缺失时相关用例自动 skip），确定性。
覆盖：
  1. notes/*.md 齐全、非空、含「来源」标注；
  2. data/key_findings.csv 可读、列齐全、关键字段非空、每行列数一致；
  3. key_findings.csv 的每条 (来源仓库, 来源文件) 指向真实存在的兄弟仓库文件；
  4. README 存在、含「关键结论」、其索引到的 notes/data 文件都存在；
  5. 仓库元文件（LICENSE/pyproject/Makefile/.gitignore/CI）齐全。
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]   # .../kairos-research
KAIROS_ROOT = REPO_ROOT.parent                     # .../kairos（兄弟仓库所在）
NOTES_DIR = REPO_ROOT / "notes"
DATA_CSV = REPO_ROOT / "data" / "key_findings.csv"
README = REPO_ROOT / "README.md"

EXPECTED_NOTES = [
    "00-overview.md",
    "01-anomaly-map.md",
    "02-ml-vs-factor.md",
    "03-multi-asset.md",
    "04-tournament.md",
    "05-risk-tail.md",
    "06-strategy-robustness.md",
    "07-execution-tca.md",
    "08-crypto-replay.md",
    "09-data-methodology.md",
    "10-limitations.md",
]

REQUIRED_CSV_COLUMNS = ["指标", "值", "单位", "来源仓库", "来源文件", "备注"]


# --------------------------------------------------------------------------- #
# 1. 笔记
# --------------------------------------------------------------------------- #
def test_expected_notes_exist_and_nonempty() -> None:
    for name in EXPECTED_NOTES:
        path = NOTES_DIR / name
        assert path.is_file(), f"缺少笔记 {name}"
        text = path.read_text(encoding="utf-8")
        assert len(text.strip()) > 200, f"{name} 内容过短，疑似空文件"


def test_notes_have_source_annotation() -> None:
    """每篇笔记都要标注来源，且不止一处。"""
    for name in EXPECTED_NOTES:
        text = (NOTES_DIR / name).read_text(encoding="utf-8")
        assert "来源" in text, f"{name} 缺少「来源」标注"
        assert text.count("来源") >= 3, f"{name} 来源标注过少（<3 处）"


def test_notes_set_matches_expected() -> None:
    actual = sorted(p.name for p in NOTES_DIR.glob("*.md"))
    assert actual == sorted(EXPECTED_NOTES), f"notes 目录与预期不符: {actual}"


def test_notes_cite_sibling_repos() -> None:
    """笔记里应出现对真实源仓库的引用（kairos-xxx）。"""
    pattern = re.compile(r"kairos-(?:factor|ml|portfolio|risk|backtest|execution|crypto|strategies|lab|data)")
    for name in EXPECTED_NOTES:
        text = (NOTES_DIR / name).read_text(encoding="utf-8")
        assert pattern.search(text), f"{name} 未引用任何 kairos 源仓库"


# --------------------------------------------------------------------------- #
# 2. key_findings.csv
# --------------------------------------------------------------------------- #
def test_key_findings_columns_complete() -> None:
    assert DATA_CSV.is_file(), "缺少 data/key_findings.csv"
    df = pd.read_csv(DATA_CSV)
    for col in REQUIRED_CSV_COLUMNS:
        assert col in df.columns, f"key_findings.csv 缺列 {col}"
    assert len(df) >= 60, f"key_findings.csv 行数过少（{len(df)}）"
    for col in ["指标", "值", "来源仓库", "来源文件"]:
        assert df[col].notna().all(), f"{col} 存在空值"
        assert (df[col].astype(str).str.strip() != "").all(), f"{col} 存在空白"


def test_key_findings_stdlib_csv_consistent() -> None:
    """用标准库再读一遍，确认表头正确、每行列数一致（无未转义逗号）。"""
    with open(DATA_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == REQUIRED_CSV_COLUMNS, f"表头不符: {rows[0]}"
    bad = [i + 1 for i, r in enumerate(rows) if len(r) != len(REQUIRED_CSV_COLUMNS)]
    assert not bad, f"以下行列数不等于 {len(REQUIRED_CSV_COLUMNS)}: {bad}"


def test_key_findings_sources_traceable() -> None:
    """每条 (来源仓库, 来源文件) 都应指向真实存在的兄弟仓库文件。

    CI 中若只 checkout 本仓库（兄弟仓库不存在），则跳过——保持离线可运行。
    """
    if not (KAIROS_ROOT / "kairos-data").is_dir():
        pytest.skip("兄弟仓库不可用（单仓库 checkout），跳过溯源校验")
    df = pd.read_csv(DATA_CSV)
    missing = []
    for _, row in df.iterrows():
        path = KAIROS_ROOT / str(row["来源仓库"]) / str(row["来源文件"])
        if not path.is_file():
            missing.append(f"{row['来源仓库']}/{row['来源文件']}")
    assert not missing, f"以下来源文件不存在: {missing}"


def test_key_findings_repos_are_known() -> None:
    df = pd.read_csv(DATA_CSV)
    known = {
        "kairos-factor", "kairos-ml", "kairos-portfolio", "kairos-risk",
        "kairos-backtest", "kairos-execution", "kairos-crypto",
        "kairos-strategies", "kairos-lab", "kairos-data",
    }
    unknown = set(df["来源仓库"].astype(str)) - known
    assert not unknown, f"出现未知来源仓库: {unknown}"


# --------------------------------------------------------------------------- #
# 3. README
# --------------------------------------------------------------------------- #
def test_readme_exists_with_key_conclusions() -> None:
    assert README.is_file(), "缺少 README.md"
    text = README.read_text(encoding="utf-8")
    assert "关键结论" in text, "README 缺少「关键结论」摘要"
    assert len(text.strip()) > 500, "README 内容过短"


def test_readme_indexed_files_exist() -> None:
    text = README.read_text(encoding="utf-8")
    refs = set(re.findall(r"(?:notes/[\w\-]+\.md|data/[\w\-]+\.csv)", text))
    assert refs, "README 未索引任何笔记/数据文件"
    for rel in refs:
        assert (REPO_ROOT / rel).is_file(), f"README 索引的文件不存在: {rel}"
    for name in EXPECTED_NOTES:
        assert f"notes/{name}" in refs, f"README 未索引 {name}"


def test_readme_key_conclusions_within_ten_bullets() -> None:
    """「关键结论」区块的 bullet 数不超过 10 条。"""
    text = README.read_text(encoding="utf-8")
    m = re.search(r"关键结论(.*?)(?:\n##|\Z)", text, flags=re.S)
    assert m, "未找到「关键结论」区块"
    bullets = [ln for ln in m.group(1).splitlines() if ln.strip().startswith(("-", "*"))]
    assert 1 <= len(bullets) <= 10, f"关键结论 bullet 数应为 1~10，实际 {len(bullets)}"


# --------------------------------------------------------------------------- #
# 4. 仓库元文件
# --------------------------------------------------------------------------- #
def test_repo_meta_files_exist() -> None:
    for rel in [
        "LICENSE",
        "pyproject.toml",
        "Makefile",
        ".gitignore",
        ".github/workflows/ci.yml",
    ]:
        assert (REPO_ROOT / rel).is_file(), f"缺少 {rel}"


def test_license_mit_and_copyright() -> None:
    text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Copyright (c) 2026 Bruce848647703" in text
