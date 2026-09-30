# 00 · 数据与方法总览

> 本篇是整套研究结论的「地基」：说清楚每个数字来自哪份真实数据、用什么口径、如何防未来函数、计了多少成本、能否复现。
> 后续每篇笔记的结论都建立在这里描述的样本与规则之上。

## 背景 / 问题

Kairos 系列（`kairos-factor` / `kairos-ml` / `kairos-portfolio` / `kairos-risk` / `kairos-backtest` / `kairos-execution` / `kairos-crypto` / `kairos-strategies` / `kairos-lab`）各自在**同一批真实行情**上跑了独立实验。要把它们的结论综合成连贯报告，必须先统一三件事：用的是哪份数据、复权口径是否一致、以及各仓库的成本/防未来设定差异——否则跨仓库的数字无法横向比较。

## 数据与方法

### 两套真实 universe（均来自 `kairos-data`，只读）

| 池 | 标的数 | 复权 | 区间 | 交易日 | 来源 |
|---|---|---|---|---|---|
| A 股（`data/ashare`） | **38** 只大盘/中盘，8 个行业 | 后复权 hfq | 2018-10-16 ~ 2026-09-24 | **1931** | (来源: kairos-data/kairos_data/universe.py `LIQUID_A_SHARES`；kairos-data/data/ashare/DATA_NOTICE.md) |
| 跨资产 ETF（`data/etf`） | **14** 只，6 个资产类别 | 后复权 hfq | 2017-08-24 ~ 2026-09-30 | **2210**（kairos-portfolio 平衡面板口径 2209、收益样本 2208） | (来源: kairos-data/kairos_data/universe.py `ASSET_CLASS_ETFS`；kairos-strategies/research/real_multi/NOTES.md；kairos-lab/research/e2e_multi_asset/REPORT.md；kairos-portfolio/research/real_portfolio/REPORT.md) |
| 黄金 ETF（`sh518880`，单标的） | 1 | 后复权 hfq | 2013-07-29 ~ 2026-09-24 | **3202** bar | (来源: kairos-crypto/research/real_replay/metrics.json) |

- A 股 8 个行业分组：consumer 6、finance 6、industrial 8、appliance 3、pharma 3、tech 4、auto_newenergy 4、energy_material 4 (来源: kairos-factor/research/real_factor/REPORT.md；kairos-data/kairos_data/universe.py `SECTORS`)。
- ETF 6 个资产类别：cn_equity（沪深300/中证500/创业板/中证1000）、cn_value（上证50/红利）、global_equity（纳指/标普500/恒生/中概互联）、commodity（黄金）、bond（国债/十年国债）、cash（货币） (来源: kairos-data/kairos_data/universe.py `ASSET_CLASSES`；kairos-strategies/research/real_multi/NOTES.md)。
- 数据源：腾讯公开行情接口 `web.ifzq.gtimg.cn`（主）/ 新浪 `money.finance.sina.com.cn`（回退），抓取代码 `kairos_data/ashare.py`（原创），字段 `date,open,high,low,close,volume` (来源: kairos-data/data/ashare/DATA_NOTICE.md)。

### 复权口径：最终统一到 hfq（后复权）

`kairos-data` 的最终提交口径为**后复权 hfq**：价格水平被放大，但**收益率正确**，适合特征/标签与回测研究 (来源: kairos-data/data/ashare/DATA_NOTICE.md；kairos-ml/research/real_ml/metrics.json `"adjust": "hfq(后复权)"`)。早期部分实验曾用前复权 qfq，踩到「负价 / 假收益」的坑后切换，详见 [09-data-methodology.md](09-data-methodology.md)。

### 各仓库的样本口径差异（同一份数据，有效样本因预热/裁剪而不同）

| 仓库 | 复权 | 有效样本 | 备注 |
|---|---|---|---|
| kairos-factor | qfq（报告口径） | 有效期 1866~1921（按因子回看期不同） | h=5 日远期收益，防未来 (来源: kairos-factor/research/real_factor/factor_ic.csv) |
| kairos-ml | hfq | 池化样本 **70908**，有效日 1866 | H=5 标签，严格 purge (来源: kairos-ml/research/real_ml/metrics.json) |
| kairos-risk | qfq + 涨跌停硬约束修复 | 收益样本 **1921**（2018-10-30 起） | 裁剪丢弃 23404 条早期价 (来源: kairos-risk/research/real_risk/risk_metrics.json) |
| kairos-backtest | qfq | **1931** bar（约 7.66 年） | 向量化 + 事件驱动 (来源: kairos-backtest/research/real_backtest/metrics.json) |
| kairos-portfolio | ETF | 2209 日（2017-08-24 ~ 2026-09-29，收益样本 2208） | 14 只 ETF、long-only SLSQP (来源: kairos-portfolio/research/real_portfolio/REPORT.md) |
| kairos-lab/e2e_multi_asset | ETF | 2210 日（2017-08-24 ~ 2026-09-30） | 14 资产、滚动再平衡 100 次 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md) |
| kairos-strategies/real_multi | ETF | 2210 期（2017-08-24 ~ 2026-09-30） | 14 资产、18 个策略、单边成本 0.05% (来源: kairos-strategies/research/real_multi/NOTES.md、SUMMARY.md) |

> 诚实提示：各报告的「38 只 / 1931 日」是同一面板，但**因子/ML/风险因回看预热与公共窗口裁剪，有效截面数并不相同**（1866 / 1906 / 1921 / 70908 等）。跨仓库比较时以各自报告口径为准，不可直接对齐期数。

### 防未来函数（全系列统一原则）

- 信号/标签只用「截至当时」的数据；权重相对信号**滞后一期**，回测器再做一期成交滞后（`held = w.shift(1)`），故实际持仓相对信号共有 2 期延迟 (来源: kairos-lab/research/e2e_equity/REPORT.md)。
- 事件驱动：`on_bar(i)` 只能取到截至第 i 根 bar 的历史，订单于第 i+1 根 bar 成交 (来源: kairos-backtest/research/real_backtest/REPORT.md)。
- ML：walk-forward 与 purged K-fold 均要求 `train_pos + H < test_first_pos`（训练标签在测试期开始前完全实现）；标准化统计量只在每折训练集内部计算 (来源: kairos-ml/research/real_ml/REPORT.md)。
- 跨包一致性校验：`kairos_ml.ic(spearman)` 与 `kairos_factor.rank_ic` 在相同截面上的最大绝对差 **1.11e-16**（两套独立实现吻合到浮点精度） (来源: kairos-lab/research/e2e_equity/REPORT.md)。

### 成本模型（各仓库不同，比较时务必对齐）

| 仓库 | 成本设定 | 来源 |
|---|---|---|
| kairos-factor | 多空价差**无成本**、等权 | kairos-factor/research/real_factor/REPORT.md |
| kairos-backtest | 佣金 3.0bp（最低 5 元）+ 滑点 5bp | kairos-backtest/research/real_backtest/metrics.json |
| kairos-strategies | 单边 0.1%（A 股）/ 0.05%（ETF） | kairos-strategies/research/real/SUMMARY.md、real_multi/SUMMARY.md |
| kairos-lab | 单边 0.1% | kairos-lab/research/e2e_equity/REPORT.md |
| kairos-execution | 滑点 2.0bp + 佣金 0.03%，参与率上限 10%/bar，latency 1 | kairos-execution/research/real_execution/tca.json |
| kairos-crypto | 手续费 0.05%，`slippage_bps=0` | kairos-crypto/research/real_replay/REPORT.md |

## 结果（数据规模速览）

- A 股池 38 只、1931 个交易日；ETF 池 14 只（6 个资产类别）、2210 个交易日（2017-08-24 ~ 2026-09-30）；黄金 ETF 单标的 3202 bar (来源: 各仓库 metrics/REPORT，见上表)。
- A 股横截面年化波动中位 0.2957、最小 0.1051（sh601398 工商银行）、最大 0.4743（sh603501 韦尔股份） (来源: kairos-risk/research/real_risk/risk_metrics.json)。
- ETF（14 只）横截面平均相关系数 0.2390，最小/最大 -0.234 / 0.951；等权组合年化波动 0.1182 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。

## 解读

整套研究的可信度取决于三点，且都已在源仓库留痕：(1) 数据是**真实公开行情**而非合成；(2) 复权口径最终统一到 hfq、收益率正确；(3) 防未来与成本设定**逐仓库明示**。正因成本口径不一，本仓库的每篇笔记都会重复标注「该数字是否含成本」，避免把无成本的多空价差与含成本的净值直接对比。

## 局限 / 后续

- **单一 universe**：38 只均为当前仍活跃的大市值龙头，存在幸存者/选择偏差，等权买入持有基准被系统性美化（详见 [10-limitations.md](10-limitations.md)）。
- **区间特定**：2018-2026 只覆盖一段行情（含 2019-2021 结构性行情与其后多轮回撤），结论不具跨市场/跨周期普适性。
- 后续：扩大到全市场（数百只以上）、引入成交量与基本面字段、对多重检验做 Bonferroni/FDR 校正。

> 相关笔记：数据坑与修复见 [09-data-methodology.md](09-data-methodology.md)；异象图谱见 [01-anomaly-map.md](01-anomaly-map.md)。
