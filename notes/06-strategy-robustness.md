# 06 · 样本外验证：哪些策略真稳健

> 问题：样本内夏普会骗人。用 walk-forward 样本外、bootstrap 置信区间、参数敏感性（OAT）、PSR 四把尺子一起量，106 个策略里哪些是真稳健、哪些是运气？
> 数据：`kairos-strategies/real/VALIDATION_SUMMARY.md`（106 策略，quick 模式：walk-forward 3 窗、bootstrap 200 次、OAT 扰动 ×0.5/×1.0/×2.0，按 PSR 降序）+ `kairos-lab/e2e_equity` 的因子 OOS。

## 背景 / 问题

[04-tournament.md](04-tournament.md) 的「夏普 Top 12」是**全样本**排名，含选择偏差。本篇用样本外验证给每个策略打分：PSR（夏普>0 的概率）、bootstrap 夏普 95% CI、walk-forward 正收益窗口占比、参数扰动后的夏普区间宽度。**四者都过关**才算稳健。

## 数据与方法

- quick 模式：walk-forward **3 个窗口**、bootstrap **200 次**、OAT（one-at-a-time）参数扰动 ×0.5/×1.0/×2.0；按 PSR 降序排列 (来源: kairos-strategies/research/real/VALIDATION_SUMMARY.md)。
- 判读维度：① PSR 高（>0.95）；② bootstrap 夏普 95% CI **下界 > 0**（显著为正）；③ 正收益窗口占比 **66.67%**（3 窗里 2 窗为正，窗口级一致）；④ 敏感性区间**宽度小**（对参数不敏感）。

## 结果

### 1. PSR 分布：从 0.996 到 0.000

- 最高 PSR：`trailing_stop_overlay` 0.996、`range_breakout` 0.993、`turn_of_month` 0.992、`donchian_turtle` 0.991、`turtle_atr` 0.990 (来源: kairos-strategies/research/real/VALIDATION_SUMMARY.md)。
- **PSR = 0.000 的有 7 个**：`liquidity_provision_ls`、`eof_stat_arb`、`reversal_ls`、`basket_neutral`、`ssd_pairs`、`quality_ls`、`xs_zscore_reversion`——全是高换手的统计套利/做市/多空类 (来源: kairos-strategies/research/real/VALIDATION_SUMMARY.md)。

### 2. 真稳健的策略（四维基本都过关）

| 策略 | 渠道 | 夏普 | PSR | bootstrap 95%CI | 正收益窗口 | 敏感性区间(宽度) |
|---|---|---|---|---|---|---|
| `turn_of_month` | seasonality | 0.85 | 0.992 | **[0.23, 1.56]** | 66.67% | 0.52~0.95 (0.43) |
| `sma_cross` | technical | 0.81 | 0.986 | **[0.04, 1.46]** | 66.67% | 0.68~0.81 (**0.13**) |
| `donchian_turtle` | technical | 0.84 | 0.991 | **[0.08, 1.44]** | 66.67% | 0.57~0.84 (0.27) |
| `turtle_atr` | trend | 0.83 | 0.990 | **[0.05, 1.44]** | 66.67% | 0.58~0.84 (0.26) |
| `carry_proxy` | crypto | 0.80 | 0.986 | **[0.02, 1.43]** | 66.67% | 0.67~0.81 (**0.14**) |
| `channel_atr_breakout` | breakout | 0.78 | 0.985 | **[0.04, 1.35]** | 66.67% | 0.51~0.83 (0.32) |
| `equal_weight_rebal` | allocation | 0.79 | 0.985 | **[0.06, 1.48]** | 66.67% | 0.77~0.79 (**0.02**) |
| `risk_parity_alloc` | allocation | 0.75 | 0.981 | **[0.07, 1.45]** | 66.67% | 0.63~0.85 (0.23) |
| `inverse_vol` | allocation | 0.72 | 0.977 | **[0.04, 1.41]** | 66.67% | 0.68~0.76 (**0.08**) |
| `equal_weight_buy_hold`（基准） | benchmark | 0.76 | 0.982 | **[0.03, 1.46]** | 66.67% | 0.76~0.76 (**0.00**) |

(来源: kairos-strategies/research/real/VALIDATION_SUMMARY.md)

> 这些策略的共同点：**bootstrap CI 下界 > 0**（夏普显著为正）、**3 窗里 2 窗为正**、且多为**低参数/低换手的趋势、季节、配置类**（`equal_weight_rebal` 敏感性宽度仅 0.02、基准无参数故 0.00）。

### 3. PSR 高 ≠ 稳健：窗口一致性陷阱

- `trailing_stop_overlay`：PSR 最高（0.996）、全样本夏普 0.96，但 **walk-forward 正收益窗口占比仅 33.33%**（3 窗里只有 1 窗为正）、窗口夏普 0.56±0.96、敏感性区间 0.57~0.98（宽度 0.41）。它的全样本高夏普**主要由特定窗口驱动**，窗口级一致性弱，单押它的尾部风险高 (来源: kairos-strategies/research/real/VALIDATION_SUMMARY.md)。
- `drawdown_throttle`（PSR 0.982）、`cppi`（PSR 0.981 但敏感性宽度 0.76）、`mom_12m_taa`（PSR 0.926、正收益窗 33.33%）同属「PSR 体面但窗口/参数不稳」一类。
- `range_breakout`（PSR 0.993）、`atr_breakout`（0.986）、`volume_imbalance`（0.983）、`macd_trend`（0.982）的 bootstrap CI 下界 ≤0（如 range_breakout [-0.00,1.53]、atr_breakout [-0.05,1.34]），**夏普未显著为正**。

### 4. 参数敏感（脆弱）与明确失败

- 敏感性区间最宽（最脆弱）：`group_momentum` 1.61、`ssd_pairs` 1.11、`adx_trend` 1.10、`max_diversification` 1.08、`dual_thrust` 0.94、`clustered_inverse_vol` 0.78、`cppi` 0.76——参数一动夏普就大幅漂移 (来源: kairos-strategies/research/real/VALIDATION_SUMMARY.md)。
- 明确不稳健（PSR≈0、bootstrap CI 全负）：`liquidity_provision_ls`（夏普 -3.01、CI [-3.68,-2.31]）、`eof_stat_arb`（-1.97）、`reversal_ls`（-1.83）、`basket_neutral`（-1.68）、`ssd_pairs`（-1.73）、`quality_ls`（-1.21）、`xs_zscore_reversion`（-1.21） (来源: kairos-strategies/research/real/VALIDATION_SUMMARY.md)。

### 5. 因子层面的 OOS（`kairos-lab/e2e_equity`，mom60）

walk-forward 26 折（train 250 / test 63）：样本内秩 IC 均值 -0.0121、**样本外秩 IC 均值 -0.0141**、符号保持比例仅 **0.5769**、多空方向命中率均值 0.5023、定向后多空 t 值均值 0.0754 (来源: kairos-lab/research/e2e_equity/REPORT.md)。即动量因子在样本外**符号都难保持**，与 [01](01-anomaly-map.md)/[02](02-ml-vs-factor.md) 的结论一致。

## 解读

- **判断稳健要四维联看**：PSR 高只是必要条件；还要 bootstrap CI 下界>0、正收益窗口占比高、敏感性区间窄。只用 PSR 排序会把 `trailing_stop_overlay` 这种「全样本冠军、窗口一致性差」的策略误判为最稳健。
- **稳健的都是低参数、低换手的趋势/季节/配置类**；**脆弱与失败的都是高换手的统计套利/做市/多空类**（PSR=0 的 7 个全在此列）。这与 A 股「短周期均值回复/做市在含成本后难盈利、而风险分散类配置更稳」的经验一致。
- 值得注意：连**等权买入持有基准**都四维过关（PSR 0.982、CI [0.03,1.46]、正窗 66.67%、无参数），说明在该幸存者偏差样本里「简单分散持有」本身就是很难被打败的稳健基线。

## 局限 / 后续

- quick 模式只有 **3 个 walk-forward 窗口、bootstrap 200 次**，窗口级统计量（如 33.33%/66.67%）粒度很粗；应做 full 模式（更多窗、更多 bootstrap）复核。
- 相关性/参数扰动基于全样本，含前视；106 个策略同时验证**未做多重检验校正**（DSR 视角见 [05-risk-tail.md](05-risk-tail.md)）。
- 后续：对四维过关的策略再做含成本、含容量的可投资性检验，并用 DSR 给「从 106 个里挑出来」这一事实打折。

> 相关笔记：策略全貌见 [04-tournament.md](04-tournament.md)；PSR/DSR 的多重检验打折见 [05-risk-tail.md](05-risk-tail.md)。
