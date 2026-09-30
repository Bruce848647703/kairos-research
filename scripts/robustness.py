#!/usr/bin/env python3
"""跨维度稳健性综合（Robustness Synthesis）。

把 `kairos-strategies` 已提交的**四类真实产物**在策略名上交叉，产出「真正稳健的策略短名单」：

1. 真实 A 股回测：`research/real/records/<name>/result.json` → sharpe / total_return / max_drawdown；
2. 样本外验证：`research/real/validation/<name>/validation.json` → psr / sharpe_ci_lo,hi /
   positive_window_ratio / sens_range / sens_sharpe_min~max；
3. 压力情景：`research/stress/stress_metrics.csv`（长表 scenario×strategy×channel）→
   worst-case 夏普（6 情景最小值）与正收益情景数（total_return>0 的情景个数）；
4. 锦标赛相关性：`research/tournament/correlation.csv` + `selection.json` → 短名单内去相关标注。

评分规则（全部由本脚本按源数据实算，不含任何手写数字）
------------------------------------------------------------------
**第一步 · 硬门槛**（任一不满足即淘汰，淘汰原因逐条记录）：

* 真实夏普 ``real_sharpe > 0``；
* ``psr >= 0.90``（夏普>0 的概率，样本外验证给出）；
* 压力正收益情景数 ``stress_pos_scenarios >= 4``（共 6 情景）；
* 压力 worst-case 夏普 ``stress_worst_sharpe >= -0.30``。

**第二步 · 综合稳健性评分**（仅对通过门槛者，截面百分位排名后等权平均，取值 0~1，越高越稳健）：

对下列 6 个维度各取 ``rank(pct=True)``（百分位，1=截面最好），再取算术平均：

* ``real_sharpe``（越大越好）
* ``psr``（越大越好）
* ``pos_window_ratio``（walk-forward 正收益窗口占比，越大越好）
* ``stress_worst_sharpe``（越大越好）
* ``stress_pos_scenarios``（越大越好）
* ``-sens_range``（参数敏感性区间宽度取负，即越窄越好）

百分位排名用 ``method="average"``，并列取平均名次，保证同一批源数据得到确定性结果。

**第三步 · 短名单与去相关标注**：综合分 Top N（默认 10，并列时按真实夏普、再按策略名排序）；
按名次贪心遍历短名单，若某策略与**已入选**策略的相关系数 > 阈值（默认取
``tournament/selection.json`` 的 ``corr_thresh``，缺失则 0.7），标记 ``redundant_flag=1``（冗余）。

输出
----
* ``data/robust_champions.csv``：短名单，列为
  ``strategy, channel, real_sharpe, real_mdd, psr, pos_window_ratio, sens_range,
  stress_worst_sharpe, stress_pos_scenarios, robustness_score, redundant_flag, rank``；
* ``data/robustness_audit.csv``（可选，``--audit``）：全体策略的四维指标 + 门槛判定与淘汰原因，
  便于复核「单维高分但综合落选」的个案；
* stdout：漏斗统计、短名单表、被淘汰的高夏普个案。

工程约束：离线（不联网）、只读源仓库、缺文件/缺维度优雅跳过并记录（不抛异常）、
仅依赖 numpy/pandas、兼容 Python 3.9。
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT: Path = REPO_ROOT.parent / "kairos-strategies" / "research"
DEFAULT_OUT: Path = REPO_ROOT / "data" / "robust_champions.csv"
DEFAULT_AUDIT: Path = REPO_ROOT / "data" / "robustness_audit.csv"

# 硬门槛：任一不满足即淘汰（阈值含义见模块 docstring）。
MIN_REAL_SHARPE: float = 0.0
MIN_PSR: float = 0.90
MIN_POS_SCENARIOS: int = 4
MIN_WORST_SHARPE: float = -0.30
N_SCENARIOS_EXPECTED: int = 6
DEFAULT_CORR_THRESH: float = 0.7
DEFAULT_TOP_N: int = 10

# 综合分的 6 个维度：(列名, 是否越大越好)。
SCORE_DIMENSIONS: Tuple[Tuple[str, bool], ...] = (
    ("real_sharpe", True),
    ("psr", True),
    ("pos_window_ratio", True),
    ("stress_worst_sharpe", True),
    ("stress_pos_scenarios", True),
    ("sens_range", False),
)

CHAMPION_COLUMNS: Tuple[str, ...] = (
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
)

AUDIT_COLUMNS: Tuple[str, ...] = (
    "strategy",
    "channel",
    "real_sharpe",
    "real_total_return",
    "real_mdd",
    "psr",
    "sharpe_ci_lo",
    "sharpe_ci_hi",
    "pos_window_ratio",
    "sens_range",
    "sens_sharpe_min",
    "sens_sharpe_max",
    "stress_worst_sharpe",
    "stress_best_sharpe",
    "stress_pos_scenarios",
    "stress_n_scenarios",
    "stress_worst_drawdown",
    "robustness_score",
    "robustness_rank",
    "gate_passed",
    "gate_reasons",
    "dims_missing",
)


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #
@dataclass
class SourceStatus:
    """源数据可用性状态（缺文件时记录而不崩溃）。"""

    available: Dict[str, bool] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def note(self, message: str) -> None:
        self.notes.append(message)


@dataclass
class SynthesisResult:
    """一次综合计算的完整结果，供写盘/打印/测试复用。"""

    audit: pd.DataFrame
    champions: pd.DataFrame
    status: SourceStatus
    corr_thresh: float
    top_n: int
    skipped: List[str] = field(default_factory=list)

    # -- 漏斗统计 ---------------------------------------------------------- #
    @property
    def n_universe(self) -> int:
        return len(self.audit)

    @property
    def n_passed(self) -> int:
        return int(self.audit["gate_passed"].astype(bool).sum())

    @property
    def gate_funnel(self) -> Dict[str, int]:
        """各门槛单独淘汰了多少策略（一个策略可能触发多条）。"""
        reasons: Dict[str, int] = {}
        failed = ~self.audit["gate_passed"].astype(bool)
        for text in self.audit.loc[failed, "gate_reasons"]:
            for item in str(text).split(";"):
                item = item.strip()
                if item:
                    reasons[item] = reasons.get(item, 0) + 1
        return dict(sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])))


# --------------------------------------------------------------------------- #
# 源数据读取（全部只读；任何缺失都降级为空表 + 记录）
# --------------------------------------------------------------------------- #
def _read_json(path: Path) -> Optional[dict]:
    """安全读取 JSON；文件不存在或解析失败返回 None。"""
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _to_float(value: object) -> float:
    """把任意标量转 float；不可转时返回 NaN（不抛异常）。"""
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float("nan")
    return out if np.isfinite(out) else float("nan")


def load_real_backtests(root: Path, status: SourceStatus) -> pd.DataFrame:
    """读取真实 A 股回测产物 ``real/records/<name>/result.json``。

    返回列：``strategy, channel, real_sharpe, real_total_return, real_mdd``。
    """
    columns = ["strategy", "channel", "real_sharpe", "real_total_return", "real_mdd"]
    records_dir = root / "real" / "records"
    if not records_dir.is_dir():
        status.available["real_records"] = False
        status.note(f"缺少真实回测目录：{records_dir}")
        return pd.DataFrame(columns=columns)

    rows: List[Dict[str, object]] = []
    for path in sorted(records_dir.glob("*/result.json")):
        payload = _read_json(path)
        if payload is None:
            status.note(f"回测产物无法解析：{path}")
            continue
        meta = payload.get("meta") or {}
        metrics = payload.get("metrics") or {}
        name = str(meta.get("name") or path.parent.name)
        rows.append(
            {
                "strategy": name,
                "channel": str(meta.get("channel") or ""),
                "real_sharpe": _to_float(metrics.get("sharpe")),
                "real_total_return": _to_float(metrics.get("total_return")),
                "real_mdd": _to_float(metrics.get("max_drawdown")),
            }
        )
    status.available["real_records"] = bool(rows)
    if not rows:
        status.note(f"{records_dir} 下未找到任何 result.json")
    return pd.DataFrame(rows, columns=columns)


def load_validations(root: Path, status: SourceStatus) -> pd.DataFrame:
    """读取样本外验证产物 ``real/validation/<name>/validation.json``。

    优先取扁平化的 ``row`` 段（与 VALIDATION_SUMMARY.md 同源），缺失时回退到
    ``psr`` / ``sharpe_ci`` / ``walk_forward`` / ``sensitivity.overall`` 嵌套字段。
    """
    columns = [
        "strategy",
        "psr",
        "sharpe_ci_lo",
        "sharpe_ci_hi",
        "pos_window_ratio",
        "sens_range",
        "sens_sharpe_min",
        "sens_sharpe_max",
    ]
    val_dir = root / "real" / "validation"
    if not val_dir.is_dir():
        status.available["validation"] = False
        status.note(f"缺少样本外验证目录：{val_dir}")
        return pd.DataFrame(columns=columns)

    rows: List[Dict[str, object]] = []
    for path in sorted(val_dir.glob("*/validation.json")):
        payload = _read_json(path)
        if payload is None:
            status.note(f"验证产物无法解析：{path}")
            continue
        row = payload.get("row") or {}
        walk = payload.get("walk_forward") or {}
        sens_overall = (payload.get("sensitivity") or {}).get("overall") or {}
        ci = payload.get("sharpe_ci") or {}
        rows.append(
            {
                "strategy": str(payload.get("name") or row.get("name") or path.parent.name),
                "psr": _to_float(row.get("psr", payload.get("psr"))),
                "sharpe_ci_lo": _to_float(row.get("sharpe_ci_lo", ci.get("lo"))),
                "sharpe_ci_hi": _to_float(row.get("sharpe_ci_hi", ci.get("hi"))),
                "pos_window_ratio": _to_float(
                    row.get("positive_window_ratio", walk.get("positive_window_ratio"))
                ),
                "sens_range": _to_float(row.get("sens_range", sens_overall.get("range"))),
                "sens_sharpe_min": _to_float(row.get("sens_sharpe_min", sens_overall.get("min"))),
                "sens_sharpe_max": _to_float(row.get("sens_sharpe_max", sens_overall.get("max"))),
            }
        )
    status.available["validation"] = bool(rows)
    if not rows:
        status.note(f"{val_dir} 下未找到任何 validation.json")
    return pd.DataFrame(rows, columns=columns)


def load_stress(root: Path, status: SourceStatus) -> pd.DataFrame:
    """读取压力情景长表 ``stress/stress_metrics.csv`` 并按策略聚合。

    聚合口径：``stress_worst_sharpe`` = 各情景夏普最小值；``stress_pos_scenarios`` =
    ``total_return > 0`` 的情景个数；``stress_worst_drawdown`` = 各情景回撤最大值。
    """
    columns = [
        "strategy",
        "channel",
        "stress_worst_sharpe",
        "stress_best_sharpe",
        "stress_mean_sharpe",
        "stress_pos_scenarios",
        "stress_n_scenarios",
        "stress_worst_drawdown",
    ]
    path = root / "stress" / "stress_metrics.csv"
    if not path.is_file():
        status.available["stress"] = False
        status.note(f"缺少压力情景表：{path}")
        return pd.DataFrame(columns=columns)
    try:
        raw = pd.read_csv(path)
    except (OSError, ValueError) as exc:  # pragma: no cover - 防御性分支
        status.available["stress"] = False
        status.note(f"压力情景表无法解析：{path}（{exc}）")
        return pd.DataFrame(columns=columns)

    required = {"scenario", "strategy", "sharpe", "total_return"}
    missing = required - set(raw.columns)
    if missing:
        status.available["stress"] = False
        status.note(f"压力情景表缺列 {sorted(missing)}：{path}")
        return pd.DataFrame(columns=columns)

    raw["sharpe"] = pd.to_numeric(raw["sharpe"], errors="coerce")
    raw["total_return"] = pd.to_numeric(raw["total_return"], errors="coerce")
    if "max_drawdown" in raw.columns:
        raw["max_drawdown"] = pd.to_numeric(raw["max_drawdown"], errors="coerce")
    else:
        raw["max_drawdown"] = np.nan

    grouped = raw.groupby("strategy", sort=True)
    out = pd.DataFrame(
        {
            "stress_worst_sharpe": grouped["sharpe"].min(),
            "stress_best_sharpe": grouped["sharpe"].max(),
            "stress_mean_sharpe": grouped["sharpe"].mean(),
            "stress_pos_scenarios": grouped["total_return"].apply(lambda s: int((s > 0).sum())),
            "stress_n_scenarios": grouped["scenario"].nunique(),
            "stress_worst_drawdown": grouped["max_drawdown"].max(),
        }
    ).reset_index()
    if "channel" in raw.columns:
        chan = grouped["channel"].agg(lambda s: str(s.iloc[0]) if len(s) else "")
        out = out.merge(chan.rename("channel").reset_index(), on="strategy", how="left")
    else:
        out["channel"] = ""
    incomplete = out.loc[out["stress_n_scenarios"] < N_SCENARIOS_EXPECTED, "strategy"].tolist()
    if incomplete:
        status.note(
            f"{len(incomplete)} 个策略压力情景数 < {N_SCENARIOS_EXPECTED}："
            f"{', '.join(map(str, incomplete[:5]))}{' 等' if len(incomplete) > 5 else ''}"
        )
    status.available["stress"] = bool(len(out))
    return out[columns]


def load_correlation(root: Path, status: SourceStatus) -> pd.DataFrame:
    """读取锦标赛两两相关矩阵 ``tournament/correlation.csv``（首列为策略名）。"""
    path = root / "tournament" / "correlation.csv"
    if not path.is_file():
        status.available["correlation"] = False
        status.note(f"缺少相关性矩阵：{path}")
        return pd.DataFrame()
    try:
        corr = pd.read_csv(path, index_col=0)
    except (OSError, ValueError) as exc:  # pragma: no cover - 防御性分支
        status.available["correlation"] = False
        status.note(f"相关性矩阵无法解析：{path}（{exc}）")
        return pd.DataFrame()
    corr = corr.apply(pd.to_numeric, errors="coerce")
    status.available["correlation"] = bool(corr.shape[0])
    return corr


def load_selection(root: Path, status: SourceStatus) -> dict:
    """读取锦标赛精选结果 ``tournament/selection.json``（用其 corr_thresh / selected）。"""
    path = root / "tournament" / "selection.json"
    payload = _read_json(path)
    if payload is None:
        status.available["selection"] = False
        status.note(f"缺少或无法解析锦标赛精选：{path}")
        return {}
    status.available["selection"] = True
    return payload


def load_all(root: Path) -> Tuple[pd.DataFrame, pd.DataFrame, SourceStatus, dict]:
    """一次性载入四维源数据，返回 (合并宽表, 相关矩阵, 状态, selection)。"""
    status = SourceStatus()
    real = load_real_backtests(root, status)
    valid = load_validations(root, status)
    stress = load_stress(root, status)
    corr = load_correlation(root, status)
    selection = load_selection(root, status)

    frames: List[pd.DataFrame] = []
    if not real.empty:
        frames.append(real)
    if not valid.empty:
        frames.append(valid)
    if not stress.empty:
        # channel 以回测产物为准，压力表仅作兜底
        frames.append(stress.drop(columns=["channel"], errors="ignore"))

    if not frames:
        status.note("四维源数据全部缺失，无法综合")
        return pd.DataFrame(), corr, status, selection

    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="strategy", how="outer", sort=True)
    if "channel" not in merged.columns:
        merged["channel"] = ""
    merged["channel"] = merged["channel"].fillna("")
    if not stress.empty and "channel" in stress.columns:
        fallback = stress.set_index("strategy")["channel"]
        blank = merged["channel"].astype(str).str.strip() == ""
        merged.loc[blank, "channel"] = (
            merged.loc[blank, "strategy"].map(fallback).fillna("").astype(str)
        )
    merged = merged.sort_values("strategy").reset_index(drop=True)
    merged["dims_missing"] = merged.apply(_missing_dims, axis=1)
    return merged, corr, status, selection


_REQUIRED_FIELDS: Tuple[str, ...] = (
    "real_sharpe",
    "psr",
    "pos_window_ratio",
    "sens_range",
    "stress_worst_sharpe",
    "stress_pos_scenarios",
)


def _missing_dims(row: pd.Series) -> str:
    """列出某策略缺失/非有限的评分维度（用于「优雅跳过并记录」）。"""
    missing = [c for c in _REQUIRED_FIELDS if not np.isfinite(_to_float(row.get(c)))]
    return ";".join(missing)


# --------------------------------------------------------------------------- #
# 门槛、评分、去相关
# --------------------------------------------------------------------------- #
def gate_reasons(row: pd.Series) -> List[str]:
    """返回某策略未通过的门槛原因列表；空列表代表全部通过。"""
    reasons: List[str] = []
    dims = str(row.get("dims_missing") or "")
    if dims:
        reasons.append("缺维度:" + dims.replace(";", "+"))
    real_sharpe = _to_float(row.get("real_sharpe"))
    psr = _to_float(row.get("psr"))
    worst = _to_float(row.get("stress_worst_sharpe"))
    pos_scen = _to_float(row.get("stress_pos_scenarios"))
    if np.isfinite(real_sharpe) and not real_sharpe > MIN_REAL_SHARPE:
        reasons.append("真实夏普<=0")
    if np.isfinite(psr) and not psr >= MIN_PSR:
        reasons.append("PSR<0.90")
    if np.isfinite(pos_scen) and not pos_scen >= MIN_POS_SCENARIOS:
        reasons.append("压力正收益情景<4")
    if np.isfinite(worst) and not worst >= MIN_WORST_SHARPE:
        reasons.append("压力worst夏普<-0.30")
    return reasons


def evaluate_gates(merged: pd.DataFrame) -> pd.DataFrame:
    """给合并宽表加 ``gate_passed`` / ``gate_reasons`` 两列。"""
    out = merged.copy()
    if out.empty:
        out["gate_passed"] = pd.Series(dtype=bool)
        out["gate_reasons"] = pd.Series(dtype=object)
        return out
    reasons = out.apply(gate_reasons, axis=1)
    out["gate_reasons"] = reasons.apply(lambda items: ";".join(items))
    out["gate_passed"] = reasons.apply(lambda items: not items)
    return out


def pct_rank(values: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """截面百分位排名（0~1，1=最好）；并列取平均名次，NaN 保持 NaN。"""
    series = pd.to_numeric(values, errors="coerce")
    if not higher_is_better:
        series = -series
    return series.rank(pct=True, method="average", na_option="keep")


def compute_robustness_score(passers: pd.DataFrame) -> pd.Series:
    """对通过门槛者按 :data:`SCORE_DIMENSIONS` 做等权百分位平均，得 0~1 综合分。"""
    if passers.empty:
        return pd.Series(dtype=float, index=passers.index)
    ranks = pd.DataFrame(index=passers.index)
    for column, higher_is_better in SCORE_DIMENSIONS:
        if column in passers.columns:
            ranks[column] = pct_rank(passers[column], higher_is_better)
    if ranks.empty:
        return pd.Series(np.nan, index=passers.index)
    return ranks.mean(axis=1, skipna=True)


def flag_redundant(
    shortlist: pd.DataFrame, corr: pd.DataFrame, thresh: float
) -> pd.Series:
    """按名次贪心去相关：与已入选策略相关系数 > thresh 者标记为冗余（1）。

    相关矩阵缺失或某策略不在矩阵中时，保守地视为「不冗余」，避免误杀。
    """
    flags = pd.Series(0, index=shortlist.index, dtype=int)
    if shortlist.empty or corr.empty:
        return flags
    accepted: List[str] = []
    for idx, row in shortlist.iterrows():
        name = str(row["strategy"])
        if name not in corr.index or name not in corr.columns:
            accepted.append(name)
            continue
        row_corr = corr.loc[name, [c for c in accepted if c in corr.columns]]
        if len(row_corr) and float(row_corr.max()) > thresh:
            flags.loc[idx] = 1
        else:
            accepted.append(name)
    return flags


def build_result(
    root: Path,
    top_n: int = DEFAULT_TOP_N,
    corr_thresh: Optional[float] = None,
) -> SynthesisResult:
    """主流程：载源 → 门槛 → 综合分 → 短名单 → 去相关标注。"""
    merged, corr, status, selection = load_all(root)
    skipped: List[str] = []

    if merged.empty:
        audit = pd.DataFrame(columns=AUDIT_COLUMNS)
        champions = pd.DataFrame(columns=CHAMPION_COLUMNS)
        return SynthesisResult(audit, champions, status, DEFAULT_CORR_THRESH, top_n, status.notes)

    gated = evaluate_gates(merged)
    for _, row in gated[gated["dims_missing"].astype(str) != ""].iterrows():
        skipped.append(f"{row['strategy']}（缺 {row['dims_missing']}）")

    passers = gated[gated["gate_passed"]].copy()
    passers["robustness_score"] = compute_robustness_score(passers)
    ordered = passers.sort_values(
        ["robustness_score", "real_sharpe", "strategy"], ascending=[False, False, True]
    ).reset_index(drop=True)
    ordered["robustness_rank"] = np.arange(1, len(ordered) + 1, dtype=int)
    gated = gated.merge(
        ordered[["strategy", "robustness_score", "robustness_rank"]], on="strategy", how="left"
    )

    thresh = corr_thresh
    if thresh is None:
        raw_thresh = _to_float(selection.get("corr_thresh"))
        thresh = raw_thresh if np.isfinite(raw_thresh) else DEFAULT_CORR_THRESH

    shortlist = ordered.head(max(int(top_n), 0)).copy()
    shortlist["rank"] = np.arange(1, len(shortlist) + 1, dtype=int)
    shortlist["redundant_flag"] = flag_redundant(shortlist, corr, thresh)

    champions = shortlist[list(CHAMPION_COLUMNS)].reset_index(drop=True)
    audit_cols = [c for c in AUDIT_COLUMNS if c in gated.columns]
    audit = gated.sort_values("strategy")[audit_cols].reset_index(drop=True)
    for column in ("gate_passed",):
        if column in audit.columns:
            audit[column] = audit[column].astype(bool).map({True: 1, False: 0})
    return SynthesisResult(audit, champions, status, float(thresh), top_n, skipped)


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #
def _format_frame(frame: pd.DataFrame, float_cols: Sequence[str]) -> pd.DataFrame:
    """把输出表的数值列统一四舍五入到 6 位，便于阅读且保留可复核精度。"""
    out = frame.copy()
    for column in float_cols:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").round(6)
    return out


def write_outputs(
    result: SynthesisResult,
    out_path: Path = DEFAULT_OUT,
    audit_path: Optional[Path] = DEFAULT_AUDIT,
) -> Tuple[Path, Optional[Path]]:
    """写短名单 CSV（以及可选的全量审计 CSV）。目录不存在时自动创建。"""
    float_cols = [
        "real_sharpe",
        "real_mdd",
        "psr",
        "pos_window_ratio",
        "sens_range",
        "stress_worst_sharpe",
        "robustness_score",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _format_frame(result.champions, float_cols).to_csv(out_path, index=False)
    written_audit: Optional[Path] = None
    if audit_path is not None:
        audit_floats = [
            c
            for c in AUDIT_COLUMNS
            if c.startswith(("real_", "psr", "sens", "sharpe", "pos_", "stress_"))
            or c == "robustness_score"
        ]
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        _format_frame(result.audit, audit_floats).to_csv(audit_path, index=False)
        written_audit = audit_path
    return out_path, written_audit


def _print_shortlist(frame: pd.DataFrame) -> None:
    """打印短名单表（等宽对齐，便于终端阅读）。"""
    if frame.empty:
        print("短名单为空：无策略同时通过四条硬门槛。")
        return
    header = (
        f"{'#':>2} {'strategy':<26} {'channel':<14} {'real_sh':>8} {'psr':>6} "
        f"{'pos_win':>7} {'sens_r':>7} {'worst':>7} {'pos_sc':>6} {'score':>6} {'redu':>5}"
    )
    print(header)
    print("-" * len(header))
    for _, row in frame.iterrows():
        print(
            f"{int(row['rank']):>2} {row['strategy']!s:<26} {row['channel']!s:<14} "
            f"{_to_float(row['real_sharpe']):>8.4f} {_to_float(row['psr']):>6.3f} "
            f"{_to_float(row['pos_window_ratio']):>7.2%} {_to_float(row['sens_range']):>7.3f} "
            f"{_to_float(row['stress_worst_sharpe']):>7.3f} "
            f"{int(_to_float(row['stress_pos_scenarios'])):>4}/6 "
            f"{_to_float(row['robustness_score']):>6.4f} {int(row['redundant_flag']):>5}"
        )


def _print_high_sharpe_rejects(result: SynthesisResult, limit: int = 8) -> None:
    """打印「真实夏普高但被门槛淘汰」的个案，用于说明单维高分不等于稳健。"""
    audit = result.audit
    if audit.empty:
        return
    rejected = audit[~audit["gate_passed"].astype(bool)].copy()
    if rejected.empty:
        print("被淘汰名单：空（全部策略通过门槛）。")
        return
    rejected = rejected.sort_values("real_sharpe", ascending=False).head(limit)
    print("\n真实夏普最高的被淘汰个案（单维高分但综合不过门槛）：")
    for _, row in rejected.iterrows():
        print(
            f"  {row['strategy']!s:<26} 真实夏普 {_to_float(row['real_sharpe']):+.4f} | "
            f"PSR {_to_float(row['psr']):.3f} | 压力正收益情景 "
            f"{int(_to_float(row['stress_pos_scenarios']))}/6 | 压力worst夏普 "
            f"{_to_float(row['stress_worst_sharpe']):+.3f} | 淘汰原因：{row['gate_reasons']}"
        )


def print_summary(result: SynthesisResult) -> None:
    """打印漏斗统计、短名单与淘汰个案。"""
    print("=" * 78)
    print("跨维度稳健性综合（真实回测 × 样本外验证 × 压力情景 × 锦标赛相关性）")
    print("=" * 78)
    for key, ok in sorted(result.status.available.items()):
        print(f"  源数据 {key:<12}: {'可用' if ok else '缺失'}")
    for note in result.status.notes:
        print(f"  [记录] {note}")
    if result.skipped:
        print(f"  [跳过] 缺维度策略 {len(result.skipped)} 个：{'、'.join(result.skipped[:5])}"
              f"{' 等' if len(result.skipped) > 5 else ''}")
    print(
        f"\n候选池 {result.n_universe} 个策略 → 通过四条硬门槛 {result.n_passed} 个"
        f"（淘汰 {result.n_universe - result.n_passed} 个）；去相关阈值 {result.corr_thresh:.2f}"
    )
    funnel = result.gate_funnel
    if funnel:
        print("门槛淘汰计数（一个策略可触发多条）：")
        for reason, count in funnel.items():
            print(f"  {reason:<28} {count:>4} 个")
    print(f"\n综合稳健性短名单 Top {min(result.top_n, len(result.champions))}：")
    _print_shortlist(result.champions)
    _print_high_sharpe_rejects(result)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """命令行参数解析。"""
    parser = argparse.ArgumentParser(
        description="跨维度稳健性综合：交叉真实回测/样本外验证/压力情景/锦标赛相关性，产出稳健策略短名单。"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help=f"kairos-strategies 研究产物根目录（只读），默认 {DEFAULT_SOURCE_ROOT}",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="短名单 CSV 输出路径")
    parser.add_argument(
        "--audit",
        type=Path,
        default=DEFAULT_AUDIT,
        help="全量四维指标+门槛判定 CSV 输出路径；传 'none' 则不写",
    )
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N, help="短名单长度 N（默认 10）")
    parser.add_argument(
        "--corr-thresh",
        type=float,
        default=None,
        help="去相关阈值；默认取 tournament/selection.json 的 corr_thresh，缺失则 0.7",
    )
    parser.add_argument("--quiet", action="store_true", help="只写文件，不打印汇总")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """脚本入口：计算 → 写盘 → 打印短名单。源数据全缺时返回 1。"""
    args = parse_args(argv)
    result = build_result(args.source, top_n=args.top, corr_thresh=args.corr_thresh)
    audit_path: Optional[Path] = None
    if args.audit is not None and str(args.audit).strip().lower() != "none":
        audit_path = args.audit
    out, audit_written = write_outputs(result, args.out, audit_path)
    if not args.quiet:
        print_summary(result)
        print(f"\n已写出：{out}")
        if audit_written is not None:
            print(f"已写出：{audit_written}")
    if result.audit.empty:
        print("错误：未能读到任何源数据，未生成短名单。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
