# 04 · 106 策略锦标赛：相关性聚类、去相关精选、精英组合

> 问题：在同一批真实 A 股上跑 106 个策略，如何从「单一最高夏普」走向「一组彼此低相关、各自较优」的精英组合？精英组合 vs 单一最佳 vs 等权基准，夏普与回撤谁更优？
> 数据：`kairos-strategies/tournament`（ashare_real，38 资产、1931 期、参与策略 106、失败 0）。

## 背景 / 问题

[real/SUMMARY.md](#) 里 106 个策略表现两极分化（最高夏普 0.96、最低 -3.01）。直接挑「样本内夏普最高」的那一个是典型的选择偏差。锦标赛的目标是：用**相关性聚类 + 去相关精选 + 分散化组合**，得到一组稳健的「精英组合」，并与单一最佳、等权基准三方对比。

## 数据与方法

- 对全部 106 个策略在同一数据上回测得到各自收益流；按收益相关距离 `sqrt(0.5·(1−ρ))` 做层次聚类；再按夏普降序**贪心纳入、跳过与已选相关性 ≥0.7 者**，选 8 个；最后用 inverse_vol 加权成精英组合 (来源: kairos-strategies/research/tournament/REPORT.md)。

## 结果

### 1. 夏普 Top 12（全样本）

| # | 策略 | 夏普 | 累计 | 波动 | 回撤 | 卡玛 |
|---|---|---|---|---|---|---|
| 1 | `trailing_stop_overlay` | 0.96 | 113.1% | 10.9% | 14.7% | 0.71 |
| 2 | `range_breakout` | 0.87 | 63.1% | 7.7% | 14.0% | 0.47 |
| 3 | `turn_of_month` | 0.85 | 62.6% | 7.8% | 12.1% | 0.54 |
| 4 | `donchian_turtle` | 0.84 | 74.1% | 9.1% | 14.3% | 0.52 |
| 5 | `turtle_atr` | 0.83 | 66.7% | 8.5% | 13.9% | 0.49 |
| 6 | `sma_cross` | 0.81 | 85.8% | 10.7% | 13.8% | 0.61 |
| 7 | `carry_proxy` | 0.80 | 84.0% | 10.7% | 14.9% | 0.55 |
| 8 | `equal_weight_rebal` | 0.79 | 154.2% | 17.5% | 30.7% | 0.42 |
| 9 | `atr_breakout` | 0.78 | 69.9% | 9.4% | 17.8% | 0.40 |
| 10 | `channel_atr_breakout` | 0.78 | 64.5% | 8.8% | 15.4% | 0.44 |
| 11 | `volume_imbalance` | 0.77 | 86.2% | 11.4% | 19.8% | 0.43 |
| 12 | `drawdown_throttle` | 0.77 | 86.5% | 11.5% | 29.9% | 0.28 |

(来源: kairos-strategies/research/tournament/REPORT.md)

### 2. 相关性聚类：6 簇，85 个策略挤在一簇

| 簇 | 策略数 | 性质 |
|---|---|---|
| **cluster_1** | **85** | 绝大多数**多头方向性**策略（动量/趋势/突破/配置/择时/因子/ensemble…）高度相关，挤成一团 |
| cluster_4 | 14 | 做市/统计套利/配对（avellaneda_stoikov、basket_neutral、eof_stat_arb、grid_mm_daily、reversal_ls…） |
| cluster_3 | 4 | 做空 beta/低波/质量（betting_against_beta、lowvol_ls、quality_ls、vol_dispersion_ls） |
| cluster_2 / 5 / 6 | 各 1 | knn_alpha / ssd_pairs / coint_pairs（孤立） |

(来源: kairos-strategies/research/tournament/REPORT.md；selection.json `clusters`)

> **关键观察**：106 个策略里 85 个落在同一相关性簇——所谓「上百个策略」的分散其实是**幻觉**，它们大多在赌同一个多头方向。真正能提供去相关收益的只有少数做空/套利/孤立簇。

### 3. 去相关精选（corr < 0.7，取 8 个）

按夏普降序贪心纳入、跳过与已选高度相关者，最终选出：
`trailing_stop_overlay`、`range_breakout`、`turn_of_month`、`risk_parity_alloc`、`mom_12m_taa`、`idio_momentum`、`rsi_reversion`、`xs_momentum_ls` (来源: kairos-strategies/research/tournament/selection.json `selected`)。

### 4. 三方对比：精英组合 vs 单一最佳 vs 基准

| 口径 | 累计收益 | CAGR | 波动 | 夏普 | 索提诺 | 最大回撤 | 卡玛 |
|---|---|---|---|---|---|---|---|
| **精英组合**（inverse_vol，8 策略） | 64.9% | 6.7% | 7.3% | **0.93** | 1.40 | **15.20%** | 0.44 |
| 单一最佳（`trailing_stop_overlay`） | 113.1% | 10.4% | 10.9% | 0.96 | 1.44 | 14.70% | 0.71 |
| 等权买入持有（基准） | 145.3% | 12.4% | 17.4% | 0.76 | 1.12 | 31.21% | 0.40 |

(来源: kairos-strategies/research/tournament/selection.json `combo_metrics`/`best_single`/`benchmark`)

## 解读

- **精英组合 vs 基准**：夏普更高（0.93 vs 0.76）、**最大回撤减半**（15.20% vs 31.21%）、波动不到一半（7.3% vs 17.4%）；代价是绝对收益大幅让渡（64.9% vs 145.3%）。这正是策略组合的价值——**用收益换风险调整后的稳健**，而非追最高收益。
- **精英组合 vs 单一最佳**：夏普相近（0.93 vs 0.96）、回撤相近（15.20% vs 14.70%），但组合收益更低（64.9% vs 113.1%）。诚实说，本例中分散化**没有跑赢单一最佳的风险调整收益**；它的真正价值在于**分散掉单策略的选择偏差**——`trailing_stop_overlay` 虽是样本内夏普冠军，但样本外正收益窗口占比仅 33.33%（3 窗里 1 窗为正，见 [06-strategy-robustness.md](06-strategy-robustness.md)），单押它的尾部风险远高于押一篮子。
- **为何分散收益有限**：85/106 策略同属一个相关簇，去相关后只剩 8 个、且其中多数仍是多头方向性策略；真正的低相关来源（做空/套利簇）本身样本内夏普为负（cluster_3/4 多为亏损策略），纳入反而拖累收益。这解释了精英组合收益偏低的根因。

## 局限 / 后续

- 相关性聚类基于**全样本收益流**，本身含前视；实盘应只用截至当时的窗口估相关。
- 精英组合用 inverse_vol 加权、未计调仓成本对组合层的额外拖累；8 个策略的挑选含贪心顺序依赖。
- 选择偏差：「夏普 Top 12」「单一最佳」都是样本内排名，未做多重检验校正（106 个策略里挑最优，DSR 会大幅缩水，见 [05-risk-tail.md](05-risk-tail.md)）。
- 后续：对聚类用滚动窗口、对精选做 PSR/DSR 校正、把做空/套利簇单独评估其作为「尾部对冲」而非「收益引擎」的价值。

> 相关笔记：106 策略全貌与样本外验证见 [06-strategy-robustness.md](06-strategy-robustness.md)；多重检验如何打折夏普见 [05-risk-tail.md](05-risk-tail.md)。
