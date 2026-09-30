"""离线测试：校验 kairos-research 文档仓库的完整性与可溯源性。

不联网、不依赖兄弟仓库（兄弟仓库缺失时相关用例自动 skip），确定性。
覆盖：
  1. notes/*.md 齐全、非空、含「来源」标注；
  2. data/key_findings.csv 可读、列齐全、关键字段非空、每行列数一致；
  3. key_findings.csv 的每条 (来源仓库, 来源文件) 指向真实存在的兄弟仓库文件；
  4. README 存在、含「关键结论」、其索引到的 notes/data 文件都存在；
  5. 仓库元文件（LICENSE/pyproject/Makefile/.gitignore/CI）齐全；
  6. 稳健性综合：scripts/robustness.py 可导入且可作为脚本运行，
     data/robust_champions.csv 结构合法（分数∈[0,1]、rank 连续、门槛自洽），
     且笔记 11 的数字与已提交产物一致（源仓库可用时还校验可复现）。
"""
from __future__ import annotations

import ast
import csv
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]   # .../kairos-research
KAIROS_ROOT = REPO_ROOT.parent                     # .../kairos（兄弟仓库所在）
NOTES_DIR = REPO_ROOT / "notes"
DATA_CSV = REPO_ROOT / "data" / "key_findings.csv"
README = REPO_ROOT / "README.md"
SCRIPT = REPO_ROOT / "scripts" / "robustness.py"
CHAMPIONS_CSV = REPO_ROOT / "data" / "robust_champions.csv"
AUDIT_CSV = REPO_ROOT / "data" / "robustness_audit.csv"
NOTE_ROBUSTNESS = NOTES_DIR / "11-robustness-synthesis.md"
SOURCE_ROOT = KAIROS_ROOT / "kairos-strategies" / "research"

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
    "11-robustness-synthesis.md",
]

REQUIRED_CSV_COLUMNS = ["指标", "值", "单位", "来源仓库", "来源文件", "备注"]

CHAMPION_COLUMNS = [
    "strategy",
    "channel",
    "real_sharpe",
    "real_mdd",
    "psr",
    "pos_window_ratio",
    "sens_range",
    "stress_worst_sharpe",
    "stress_pos_scenarios",
    "robustness_score",
    "redundant_flag",
    "rank",
]

# 与 scripts/robustness.py 的门槛常量一致（此处独立写死，防止脚本被悄悄放宽）。
GATE_MIN_REAL_SHARPE = 0.0
GATE_MIN_PSR = 0.90
GATE_MIN_POS_SCENARIOS = 4
GATE_MIN_WORST_SHARPE = -0.30


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


# --------------------------------------------------------------------------- #
# 5. 跨维度稳健性综合（scripts/robustness.py + data/robust_champions.csv + 笔记 11）
# --------------------------------------------------------------------------- #
def _load_robustness_module():
    """按文件路径导入 ``scripts/robustness.py``（``scripts/`` 不是包）。

    Python 3.9 的 ``dataclasses`` 会去 ``sys.modules`` 查模块命名空间，
    因此这里先把模块注册进去再 exec，避免 ``AttributeError``。
    """
    spec = importlib.util.spec_from_file_location("kairos_robustness_script", SCRIPT)
    assert spec is not None and spec.loader is not None, "无法为 robustness.py 创建 import spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


@pytest.fixture(scope="module")
def robustness():
    if not SCRIPT.is_file():
        pytest.skip("缺少 scripts/robustness.py")
    return _load_robustness_module()


@pytest.fixture(scope="module")
def champions() -> pd.DataFrame:
    if not CHAMPIONS_CSV.is_file():
        pytest.skip("缺少 data/robust_champions.csv（先运行 python3 scripts/robustness.py）")
    return pd.read_csv(CHAMPIONS_CSV)


def test_robustness_script_exists_and_importable(robustness) -> None:
    """脚本可被导入，且暴露稳定的 API 与门槛常量。"""
    for attr in ("main", "build_result", "write_outputs", "CHAMPION_COLUMNS"):
        assert hasattr(robustness, attr), f"robustness.py 缺少 {attr}"
    assert list(robustness.CHAMPION_COLUMNS) == CHAMPION_COLUMNS
    assert robustness.MIN_REAL_SHARPE == GATE_MIN_REAL_SHARPE
    assert robustness.MIN_PSR == GATE_MIN_PSR
    assert robustness.MIN_POS_SCENARIOS == GATE_MIN_POS_SCENARIOS
    assert robustness.MIN_WORST_SHARPE == GATE_MIN_WORST_SHARPE


def test_robustness_script_docstring_documents_rules() -> None:
    """规则必须写在脚本 docstring 里（门槛 + 综合分 + 短名单）。"""
    text = SCRIPT.read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(text)) or ""
    lowered = doc.lower()
    for keyword in ("硬门槛", "psr", "百分位", "等权", "去相关", "redundant_flag"):
        assert keyword in lowered, f"robustness.py docstring 未说明「{keyword}」"


def test_robustness_handles_missing_source_gracefully(robustness, tmp_path: Path) -> None:
    """源目录不存在时不得抛异常：返回空表并记录说明。"""
    result = robustness.build_result(tmp_path / "does-not-exist", top_n=5)
    assert result.audit.empty and result.champions.empty
    assert list(result.champions.columns) == CHAMPION_COLUMNS
    assert result.status.notes, "缺源时应留下可读的记录"
    assert result.n_universe == 0 and result.n_passed == 0


def test_robustness_script_runs_offline(robustness, tmp_path: Path) -> None:
    """作为脚本运行：源仓库可用则产出短名单，不可用则退出码非 0 且不崩。"""
    if not SOURCE_ROOT.is_dir():
        pytest.skip("兄弟仓库 kairos-strategies 不可用，跳过脚本运行校验")
    out = tmp_path / "champions.csv"
    audit = tmp_path / "audit.csv"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(SOURCE_ROOT),
            "--out",
            str(out),
            "--audit",
            str(audit),
            "--top",
            "5",
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, f"脚本运行失败：\n{proc.stdout}\n{proc.stderr}"
    assert out.is_file() and audit.is_file()
    frame = pd.read_csv(out)
    assert list(frame.columns) == CHAMPION_COLUMNS
    assert len(frame) == 5
    assert list(frame["rank"]) == [1, 2, 3, 4, 5]
    assert "综合稳健性短名单" in proc.stdout


def test_robustness_result_is_deterministic(robustness) -> None:
    """同一批源数据两次计算结果完全一致（无随机、无时间依赖）。"""
    if not SOURCE_ROOT.is_dir():
        pytest.skip("兄弟仓库 kairos-strategies 不可用，跳过复现校验")
    first = robustness.build_result(SOURCE_ROOT, top_n=5).champions
    second = robustness.build_result(SOURCE_ROOT, top_n=5).champions
    pd.testing.assert_frame_equal(first, second)


def test_champions_csv_columns_and_ranges(champions: pd.DataFrame) -> None:
    assert list(champions.columns) == CHAMPION_COLUMNS, f"列不符：{list(champions.columns)}"
    assert len(champions) >= 1, "短名单为空"
    assert champions["strategy"].is_unique, "短名单出现重复策略"
    score = pd.to_numeric(champions["robustness_score"])
    assert score.notna().all() and score.between(0.0, 1.0).all(), "robustness_score 应在 [0,1]"
    rank = pd.to_numeric(champions["rank"]).astype(int)
    assert list(rank) == list(range(1, len(champions) + 1)), f"rank 不连续：{list(rank)}"
    assert set(champions["redundant_flag"].unique()) <= {0, 1}, "redundant_flag 只能是 0/1"
    assert champions.loc[rank.idxmin(), "redundant_flag"] == 0, "rank 1 不应被标为冗余"
    for column in ("real_sharpe", "psr", "stress_worst_sharpe", "stress_pos_scenarios"):
        assert pd.to_numeric(champions[column]).notna().all(), f"{column} 存在空值"


def test_champions_satisfy_hard_gates(champions: pd.DataFrame) -> None:
    """短名单里每个策略都必须真的通过四条硬门槛。"""
    assert (champions["real_sharpe"] > GATE_MIN_REAL_SHARPE).all()
    assert (champions["psr"] >= GATE_MIN_PSR).all()
    assert (champions["stress_pos_scenarios"] >= GATE_MIN_POS_SCENARIOS).all()
    assert (champions["stress_worst_sharpe"] >= GATE_MIN_WORST_SHARPE).all()


def test_champions_reproducible_from_source(robustness, champions: pd.DataFrame) -> None:
    """已提交的 robust_champions.csv 必须能被脚本从源数据复现。"""
    if not SOURCE_ROOT.is_dir():
        pytest.skip("兄弟仓库 kairos-strategies 不可用，跳过溯源校验")
    rebuilt = robustness.build_result(SOURCE_ROOT, top_n=len(champions)).champions
    pd.testing.assert_frame_equal(
        rebuilt.reset_index(drop=True),
        champions.reset_index(drop=True),
        check_dtype=False,
        atol=1e-6,
        rtol=0,
    )


def test_audit_csv_structure() -> None:
    if not AUDIT_CSV.is_file():
        pytest.skip("缺少 data/robustness_audit.csv")
    audit = pd.read_csv(AUDIT_CSV)
    for column in ("strategy", "gate_passed", "gate_reasons", "dims_missing", "robustness_score"):
        assert column in audit.columns, f"audit 缺列 {column}"
    assert set(audit["gate_passed"].unique()) <= {0, 1}
    passed = audit[audit["gate_passed"] == 1]
    assert len(passed) >= 1, "没有任何策略通过门槛，疑似源数据异常"
    assert passed["robustness_score"].notna().all()
    assert audit[audit["gate_passed"] == 0]["robustness_score"].isna().all()


def test_robustness_note_exists_and_traceable() -> None:
    text = NOTE_ROBUSTNESS.read_text(encoding="utf-8")
    assert len(text.strip()) > 1000, "笔记 11 内容过短"
    assert text.count("来源") >= 3, "笔记 11 来源标注过少"
    assert "kairos-strategies" in text, "笔记 11 未引用源仓库"
    for ref in (
        "scripts/robustness.py",
        "robust_champions.csv",
        "real/records",
        "real/validation",
        "stress/stress_metrics.csv",
        "tournament/correlation.csv",
    ):
        assert ref in text, f"笔记 11 未标注来源/产物 {ref}"
    for section in ("背景", "方法", "结果", "解读", "局限"):
        assert section in text, f"笔记 11 缺少「{section}」小节"


def test_robustness_note_numbers_match_csv(champions: pd.DataFrame) -> None:
    """笔记里的短名单数字必须与 robust_champions.csv 一致（防止手抄漂移）。"""
    text = NOTE_ROBUSTNESS.read_text(encoding="utf-8")
    for _, row in champions.iterrows():
        assert str(row["strategy"]) in text, f"笔记 11 未出现短名单策略 {row['strategy']}"
        rendered = f"{float(row['robustness_score']):.4f}"
        assert rendered in text, f"笔记 11 缺少综合分 {rendered}（{row['strategy']}）"


def test_readme_indexes_robustness_artifacts() -> None:
    text = README.read_text(encoding="utf-8")
    assert "notes/11-robustness-synthesis.md" in text, "README 未索引笔记 11"
    assert "data/robust_champions.csv" in text, "README 未索引 robust_champions.csv"
    assert "scripts/robustness.py" in text, "README 未提及稳健性综合脚本"

