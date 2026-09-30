# 11 · 跨维度稳健性综合：四维交叉后的「真正稳健短名单」

> 问题：前面每篇都只在**一个维度**上给策略排序——真实回测夏普（[04](04-tournament.md)）、样本外 PSR/CI（[06](06-strategy-robustness.md)）、压力情景 worst-case（`STRESS_SUMMARY.md`）、锦标赛去相关精选（[04](04-tournament.md)）。四张榜单的头部**并不重合**。那到底哪些策略是「四个维度一起看都活下来」的？
> 方法：`scripts/robustness.py` 离线读取四类源产物，按策略名 join，实算硬门槛 + 综合稳健性评分 + 去相关标注，输出 `data/robust_champions.csv`（短名单）与 `data/robustness_audit.csv`（106 策略全量四维指标 + 淘汰原因）。**本篇所有数字均由该脚本实算产出，不手写。**

## 背景 / 问题

单维排序的失败模式很具体：

- 真实回测夏普第 1 的 `trailing_stop_overlay`（0.9618）在 [06](06-strategy-robustness.md) 里已被指出 walk-forward 正收益窗口只有 33.33%；
- PSR 榜头部的一批趋势/突破策略（`range_breakout` 0.9926、`donchian_turtle` 0.9906）在**震荡市情景**里夏普崩塌到 -4 附近；
- 压力情景里 worst-case 最好的 `correlation_regime`（+0.0422）真实夏普只有 0.6922；
- 锦标赛的 8 个去相关精英是按**全样本收益**选的，没有经过样本外与压力检验。

所以需要一个**同时**用上四维证据的可复现筛选：`kairos-strategies` 的真实回测产物、样本外验证产物、合成压力情景产物、锦标赛相关矩阵。

## 四维数据与方法

| 维度 | 源文件（只读） | 取用字段 |
|---|---|---|
| ① 真实 A 股回测 | `kairos-strategies/research/real/records/<name>/result.json`（106 个） | `metrics.sharpe` / `total_return` / `max_drawdown` |
| ② 样本外验证 | `kairos-strategies/research/real/validation/<name>/validation.json`（106 个） | `psr`、`sharpe_ci_lo/hi`、`positive_window_ratio`、`sens_range`、`sens_sharpe_min~max` |
| ③ 压力情景 | `kairos-strategies/research/stress/stress_metrics.csv`（636 行 = 106 策略 × 6 情景） | 按策略聚合：`worst = min(sharpe)`、`正收益情景数 = #{total_return>0}`、`最差回撤 = max(max_drawdown)` |
| ④ 锦标赛相关性 | `kairos-strategies/research/tournament/correlation.csv` + `selection.json` | 106×106 相关矩阵；`corr_thresh=0.70` |

四维覆盖完全对齐：**106 个策略在四个源里都有数据，无一缺失、无跳过**（`robust_champions.csv`/`robustness_audit.csv` 由脚本生成，缺维度会记录在 `dims_missing` 列并优雅跳过）。

**规则（写死在 `scripts/robustness.py` 的常量里，改阈值即可复算）**：

1. **硬门槛**（任一不满足即淘汰）：真实夏普 > 0；PSR ≥ 0.90；压力正收益情景数 ≥ 4/6；压力 worst-case 夏普 ≥ -0.30。
2. **综合稳健性评分**（只对通过门槛者）：把 `真实夏普、PSR、正收益窗口占比、压力 worst 夏普、压力正收益情景数、-参数敏感区间(sens_range)` 六个维度各做**截面百分位排名**（`rank(pct=True)`，并列取平均），再**等权平均**，得 0~1 分，越高越稳健。
3. **短名单**：综合分 Top 10（并列时按真实夏普、再按策略名，保证确定性）；再按名次贪心做**去相关标注**——与已入选策略相关系数 > 0.70（阈值取自 `selection.json` 的 `corr_thresh`）者标 `redundant_flag=1`。

## 结果

### 1. 门槛漏斗：106 → 13

按门槛顺序逐层筛（来源：`data/robustness_audit.csv`，由 `scripts/robustness.py` 交叉 `research/real/*` 与 `research/stress/stress_metrics.csv` 实算）：

| 步骤 | 剩余策略数 | 本步淘汰 |
|---|---|---|
| 候选池（四维齐全） | 106 | — |
| 真实夏普 > 0 | 79 | 27 |
| PSR ≥ 0.90 | 41 | 38 |
| 压力正收益情景 ≥ 4/6 | 40 | 1 |
| 压力 worst 夏普 ≥ -0.30 | **13** | 27 |

单条门槛各自淘汰多少（一个策略可触发多条）：**压力 worst 夏普 < -0.30 淘汰 77 个（最紧）**、PSR < 0.90 淘汰 65 个、压力正收益情景 < 4 淘汰 38 个、真实夏普 ≤ 0 淘汰 27 个 (来源: kairos-strategies/research/stress/stress_metrics.csv + research/real/validation/*/validation.json，经 `data/robustness_audit.csv` 汇总)。

### 2. 稳健短名单 Top 10

全部数字来自 `data/robust_champions.csv`（脚本实算，源为 `kairos-strategies/research/real/records|validation` 与 `research/stress/stress_metrics.csv`）：

| # | 策略 | 渠道 | 真实夏普 | 真实回撤 | PSR | 正收益窗口 | sens_range | 压力 worst 夏普 | 正收益情景 | 综合分 | 冗余 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `equal_weight_rebal` | allocation | 0.7851 | 30.66% | 0.9851 | 66.67% | **0.016** | -0.037 | 5/6 | **0.7949** | 否 |
| 2 | `equal_weight_buy_hold`（基准） | benchmark | 0.7587 | 31.21% | 0.9820 | 66.67% | **0.000** | -0.045 | 5/6 | 0.7436 | 是 |
| 3 | `inverse_vol` | allocation | 0.7218 | 22.86% | 0.9770 | 66.67% | 0.081 | -0.037 | 5/6 | 0.6667 | 是 |
| 4 | `risk_parity_alloc` | allocation | 0.7496 | 22.63% | 0.9807 | 66.67% | 0.227 | -0.041 | 5/6 | 0.6410 | 是 |
| 5 | `low_beta_timing` | defensive | 0.7286 | 23.90% | 0.9778 | 66.67% | 0.203 | -0.042 | 5/6 | 0.6154 | 是 |
| 6 | `correlation_regime` | dispersion | 0.6922 | 32.29% | 0.9720 | 66.67% | 0.418 | **+0.042** | 5/6 | 0.5769 | 是 |
| 7 | `dca` | crypto | 0.6657 | 31.21% | 0.9668 | 66.67% | 0.158 | -0.067 | 5/6 | 0.5385 | 是 |
| 8 | `turn_of_month` | seasonality | **0.8520** | **12.09%** | **0.9916** | 66.67% | 0.427 | -0.268 | 4/6 | 0.5064 | **否** |
| 9 | `cppi` | riskmgmt | 0.7547 | 31.21% | 0.9815 | 66.67% | 0.759 | -0.204 | 5/6 | 0.5000 | 是 |
| 10 | `beta_timing` | regime | 0.6509 | 28.47% | 0.9636 | 66.67% | 0.202 | -0.103 | 5/6 | 0.4744 | 是 |

通过门槛但未进 Top 10 的 3 个（综合分见 `data/robustness_audit.csv` 的 `robustness_score` 列）：`vol_target` 0.3397、`max_diversification` 0.3077、`hrp` 0.2949。

### 3. 去相关后只剩 2 个「真正独立」的稳健策略

短名单 10 个策略两两共 45 对相关，**36 对 > 0.70**，中位数高达 **0.9639**，最高一对 `equal_weight_buy_hold` × `cppi` 相关 **1.0000**（`dca`、`cppi` 的真实回撤也都是 31.21%，与基准完全一致——它们本质是「一直持有 + 一点闸门」）(来源: kairos-strategies/research/tournament/correlation.csv)。

贪心去相关（阈值 0.70）后 `redundant_flag=0` 的只有两个：

| 保留 | 综合分 | 与另一保留者的相关 |
|---|---|---|
| `equal_weight_rebal`（rank 1） | 0.7949 | 0.4462 |
| `turn_of_month`（rank 8） | 0.5064 | 0.4462 |

即：**「稳健短名单」的信息量其实只有 2 个独立赌注**——一个风险预算型分散配置，一个季节性（月初效应）择时；其余 8 个都是同一个「等权多头 beta」的变体。

### 4. 门槛是「压力维度」在筛人：绑定情景 = `high_vol`

13 个通过者的 worst-case 情景里，**12 个是 `high_vol`**（唯一例外是 `turn_of_month` 的 `crash`，-0.268）。而 `high_vol` 是 6 情景里最难的：**106 个策略里只有 8 个在该情景正收益**（`month_of_year` +48.73%、`bollinger_reversion` +26.57%、`zscore_reversion` +24.65% 等），基准 `equal_weight_buy_hold` 在该情景夏普 -0.045、累计 -47.65% (来源: kairos-strategies/research/stress/stress_metrics.csv)。

全样本看，worst-case 情景的分布是：`choppy` 42 个、`high_vol` 41 个、`sector_rotation` 11 个、`crash` 5 个、`trend_up` 4 个、`bubble` 3 个——**「震荡市 + 高波市」两个情景杀掉了 83/106 的策略** (来源: kairos-strategies/research/stress/stress_metrics.csv)。

## 解读

**为什么活下来的是这些？** 通过门槛的 13 个里，渠道分布是 allocation 4、defensive/dispersion/riskmgmt/crypto/hrp/regime/seasonality/volatility/benchmark 各 1，**没有一个纯 trend/technical/breakout 策略**。共同点是：不预测方向、靠分散或压低敞口把 worst-case 托在 -0.30 以上，同时参数少（`equal_weight_rebal` 的 `sens_range` 只有 0.016、基准 0.000），因此 PSR 与窗口一致性都高。这与 [06](06-strategy-robustness.md) 的「稳健的都是低参数低换手的趋势/季节/配置类」一致，但把结论收紧了一步：**在真实回测里最能打的趋势类，恰恰在压力维度全军覆没。**

**单维高分但综合落选的典型**（数字见 `data/robustness_audit.csv`）：

| 策略 | 强在哪一维 | 倒在哪个门槛 |
|---|---|---|
| `trailing_stop_overlay` | 真实夏普 **0.9618（第 1）**、PSR **0.9956（第 1）** | 压力 worst **-0.383**（`high_vol`）< -0.30；正收益窗口也只有 33.33% |
| `range_breakout` | 真实夏普 0.8679（第 2）、PSR 0.9926 | 压力 worst **-3.959**（`choppy`） |
| `donchian_turtle` / `turtle_atr` / `atr_breakout` | PSR 0.9906 / 0.9896 / 0.9859 | 压力 worst **-3.816 / -3.807 / -4.297**（均 `choppy`） |
| `equal_weight_ensemble` | `sens_range` **0.000**（参数最不敏感）、PSR 0.9773 | 压力 worst **-1.608** |
| `vol_target_taa` / `portfolio_vol_target` / `min_variance_alloc` | 压力 worst **-0.021 / -0.031 / -0.037**（抗压榜前 4） | PSR **0.8924 / 0.8745 / 0.8784** < 0.90 |
| `month_of_year` | `high_vol` 情景夏普 **+0.5318（该情景第 1）** | 真实夏普仅 0.1195、PSR 0.6295 |
| `circuit_breaker` / `drawdown_throttle` | 真实夏普 0.5721 / 0.7656、PSR 0.9428 / 0.9823 | 压力 worst **-0.337 / -0.449**，差一点点 |

这张表说明**四个维度不可互相替代**：真实夏普衡量「历史赚不赚」，PSR/窗口衡量「是不是运气」，压力 worst 衡量「换个性格会不会崩」，相关性衡量「和别的赌注是不是一回事」。`trailing_stop_overlay` 是前两维的双料冠军，却在第三维直接出局；`month_of_year` 正好相反。

**与锦标赛精选的对照**：`selection.json` 的 8 个去相关精英里，只有 **2 个**通过四维门槛——`risk_parity_alloc`（综合第 4，0.6410）与 `turn_of_month`（综合第 8，0.5064）；其余 6 个（`trailing_stop_overlay`、`range_breakout`、`mom_12m_taa`、`idio_momentum`、`rsi_reversion`、`xs_momentum_ls`）全部倒在压力或 PSR 门槛 (来源: kairos-strategies/research/tournament/selection.json + `data/robustness_audit.csv`)。也就是说，[04](04-tournament.md) 里那个夏普 0.93、回撤 15.20% 的精英组合，其**成分的选择依据并不含样本外与压力证据**。

**基准依然难被打败**：`equal_weight_buy_hold` 自己排综合第 2（0.7436）。13 个通过门槛者里，真实夏普高于基准 0.7587 的只有 **2 个**——`equal_weight_rebal`（0.7851）与 `turn_of_month`（0.8520）；而真实回撤优于基准 31.21% 的通过者里，只有 `turn_of_month`（12.09%）是数量级的改善，`inverse_vol`（22.86%）、`risk_parity_alloc`（22.63%）、`low_beta_timing`（23.90%）改善有限，`equal_weight_rebal`（30.66%）、`cppi`/`dca`（31.21%）基本与基准持平 (来源: kairos-strategies/research/real/records/*/result.json，经 `data/robustness_audit.csv` 汇总)。

## 局限

- **压力情景是合成行情**（`kairos_strategies/scenarios.py` 固定 seed 生成，8 资产 × 1000 期），不是真实历史；`worst ≥ -0.30` 这条最紧的门槛因此建立在合成数据的性格设定上，阈值本身有主观性（改成 -0.50 会放进 `trailing_stop_overlay`、`circuit_breaker` 等）。
- **门槛口径不统一**：`stress_metrics.csv` 里的 `equal_weight_buy_hold`（周期再平衡、含 0.1% 单边成本）与 `STRESS_SUMMARY.md` 表头的「基准」（期初等权、不再平衡）不是同一序列——同一情景下累计分别 -47.65% vs -59.1%（`high_vol`）。本篇一律以 `stress_metrics.csv` 的策略行为准。
- **样本外证据很薄**：验证为 quick 模式（walk-forward 3 窗、bootstrap 200 次），`pos_window_ratio` 只能取 0/33.33%/66.67% 三个值，Top 10 全是 66.67%，这一维在短名单内几乎不区分（见 [06](06-strategy-robustness.md)）。
- **百分位等权 = 隐含的价值判断**：六维等权、且只在通过门槛的 13 个里再排名，小样本下百分位粒度很粗——`stress_pos_scenarios` 只有 4/5 两种取值，12 个策略并列拿到同一个百分位 0.577，唯一 4/6 的 `turn_of_month` 直接掉到 0.077；`pos_window_ratio` 也只有 0.077/0.577 两档（12 个通过者都是 66.67%）。未做多重检验校正——「从 106 个里挑 13 个再挑 10 个」这件事本身会高估稳健性（DSR 视角见 [05](05-risk-tail.md)）。
- **相关性来自全样本**，含前视；去相关只做「标注」不做「重选」，因此短名单里 8/10 是冗余的同一赌注。
- 幸存者偏差、单一 universe、成本与容量约束等系统性局限见 [10-limitations.md](10-limitations.md)。

## 复现

```bash
cd kairos-research
python3 scripts/robustness.py                 # 读四维源产物 → 写 data/robust_champions.csv + robustness_audit.csv → 打印短名单
python3 scripts/robustness.py --top 5 --corr-thresh 0.6 --audit none   # 改规则复算
python3 -m pytest -q                          # 含短名单结构校验
```

> 相关笔记：策略全貌与锦标赛见 [04-tournament.md](04-tournament.md)；单维样本外验证见 [06-strategy-robustness.md](06-strategy-robustness.md)；多资产配置的稳健性见 [03-multi-asset.md](03-multi-asset.md)；总体局限见 [10-limitations.md](10-limitations.md)。
> **本笔记仅供研究，不构成投资建议。**
