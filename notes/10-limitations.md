# 10 · 局限：这些结论能在多大程度上被相信

> 本篇汇总全系列研究的共性局限，每条都尽量用源报告里的真实证据支撑，避免空泛声明。
> 核心态度：**诚实优先**。负结果（无稳健单因子 alpha、ML 样本外无预测力、多数择时跑不赢等权基准）已如实写在各篇，这里说明它们为何**只能更强、不能更弱**地被相信。

## 背景 / 问题

整套研究建立在「38 只 A 股 + 9 只 ETF」的真实但**有限**的样本上。要让结论可信，必须把幸存者偏差、单一 universe、过拟合/多重检验、成本缺失、数据口径等问题逐条摊开，并说明每条对结论的影响方向。

## 七类局限（带真实证据）

### 1. 幸存者 / 选择偏差（影响：高估基准与策略表现）

- 38 只标的均为**事后精选、当前仍活跃的大市值龙头**，未含退市/长期停牌标的，存在生存偏差；等权买入持有基准因此被**系统性美化**，「因子/策略跑输等权基准」在本样本里并不意外 (来源: kairos-ml/research/real_ml/REPORT.md；kairos-backtest/research/real_backtest/REPORT.md；kairos-lab/research/e2e_equity/REPORT.md)。
- 该基准**不代表可投资的指数收益**，只用于对照口径 (来源: kairos-lab/research/e2e_equity/REPORT.md)。

### 2. 单一 universe / 单一区间（影响：不具普适性）

- 仅 38 只 A 股（8 行业、单层约 8 只）+ 9 只 ETF；截面太小、统计噪声大，IC 的标准误本身就与信号量级相当 (来源: kairos-factor/research/real_factor/REPORT.md)。
- 区间 2018-10 ~ 2026-09 只覆盖一段特定行情（含 2019-2021 结构性行情与其后多轮回撤），结论**不具备跨市场/跨周期普适性** (来源: kairos-ml/research/real_ml/REPORT.md)。
- 多资产仅 9 个资产、2354 个交易日，PSR/DSR 受样本长度限制 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。

### 3. 合成 vs 真实（影响：本系列全为真实，但有两处替代）

- 本系列**全部使用真实公开行情**（腾讯/新浪接口），非合成数据 (来源: kairos-data/data/ashare/DATA_NOTICE.md)。
- 两处合规替代：① **加密实时源在采集环境不可达**，用真实黄金 ETF 历史 bar 回放替代真实加密行情（[08](08-crypto-replay.md)）；② 执行为**纯内存模拟撮合**，不接真实券商通道，滑点/佣金/参与率均为设定值（[07](07-execution-tca.md)）。

### 4. 过拟合 / 多重检验（影响：显著性被高估，必须打折）

- 各仓库一次检验大量组合且**未做多重检验校正**：factor 16 个（样本×因子×预处理）组合、ml 3 模型×2 CV×16 特征、strategies 106 个策略、tournament 从 106 里挑 8 个 (来源: kairos-factor/research/real_factor/REPORT.md；kairos-ml/research/real_ml/REPORT.md；kairos-strategies/research/tournament/REPORT.md)。
- 在 5% 水平上，16 个组合本就期望出现约 1 个「假显著」，单看 t 值极易过拟合 (来源: kairos-factor/research/real_factor/REPORT.md)。
- **量化代价**：同一历史夏普，PSR=0.983（N=1），但承认在 38 只里挑组合后 DSR 降到 0.480（N=38）、N=100 时仅 0.341（门槛 SR₀ 抬到 0.0578） (来源: kairos-risk/research/real_risk/risk_metrics.json `backtest.dsr`)。
- 期望收益采用**已实现均值（前视）**，样本内最大夏普（1.976）对输入高度敏感、存在过拟合，实盘期望应显著更低 (来源: kairos-portfolio/research/real_portfolio/REPORT.md)。

### 5. 成本与约束缺失（影响：净收益远低于毛收益）

- factor 多空价差**无成本、无约束**，未考虑涨跌停不可成交、停牌与股票池调整；5 日调仓的单边换手会让价差大幅缩水 (来源: kairos-factor/research/real_factor/REPORT.md)。
- ml PnL 为**毛收益**，未扣佣金/印花税/冲击/融券成本；H=5 日调仓换手不低，实盘净收益会显著更低 (来源: kairos-ml/research/real_ml/REPORT.md)。
- backtest 仅建模佣金 3bp + 固定滑点 5bp，未含涨跌停、停牌、冲击成本、税费与借券约束 (来源: kairos-backtest/research/real_backtest/REPORT.md)。
- 真实成本量级参考：向量化动量累计换手 85.9x（双边）、成本拖累约 6.87%（毛→净） (来源: kairos-backtest/research/real_backtest/metrics.json)。

### 6. 数据口径（影响：早期收益/波动可能偏保守）

- qfq/hfq 跨仓库混用（factor/backtest/risk 按 qfq 描述并修复，ml/execution/crypto/lab 用 hfq）；收益率口径一致但价格水平不可直接对齐（[09](09-data-methodology.md)）。
- 前复权下界修复是**保守估计**：高分红标的早期（2019-2021）收益仍可能被小幅高估、波动/VaR 偏保守（偏大）；停牌 ffill 会低估当期波动 (来源: kairos-risk/research/real_risk/REPORT.md；kairos-factor/research/real_factor/REPORT.md)。

### 7. 结构性局限（影响：部分结论是样本内现象）

- 执行算法排序由**单一历史窗口的价格路径**驱动，换窗口（尤其趋势反向）排序会变，不构成一般性结论（[07](07-execution-tca.md)，来源: kairos-execution/research/real_execution/REPORT.md）。
- risk 的市场因子由**同一篮子等权**构成（代理市场，非独立基准）；静态权重不含调仓与成本 (来源: kairos-risk/research/real_risk/REPORT.md)。
- 单标的择时（双均线 sh600519）高度依赖标的与参数，不具横截面代表性 (来源: kairos-backtest/research/real_backtest/REPORT.md)。

## 解读：结论该被怎样相信

- **负结果比正结果更可信**：「无稳健单因子 alpha」「ML 样本外无预测力」「多数择时/套利跑不赢等权基准」这些结论，在加入成本、扩大样本、做多重检验校正后**只会更成立**（偏差方向一致）。
- **正结果需谨慎**：任何达到 |t|≥2 的项（如低波 rv10 样本外 t=-5.00）都还必须先通过交易成本、容量与多重检验的考验；本系列不把它们当作可实盘的 alpha (来源: kairos-ml/research/real_ml/REPORT.md)。
- **方法论 > 具体数字**：本仓库的真正价值是「防未来 + 留痕清洗 + 样本外验证 + PSR/DSR 打折 + 诚实呈现负结果」这套可复现的研究范式，而非某个具体夏普。

## 后续改进清单

1. 扩大到全市场（数百只以上）、引入退市/长期停牌标的以缓解幸存者偏差。
2. 引入成交量与基本面字段、加交易成本与容量约束。
3. 对多重检验做 Bonferroni / FDR 校正，统一用 DSR 报告「挑出来」的代价。
4. 统一复权口径（全 hfq）并重跑 factor/backtest/risk。
5. 在可联网环境接入真实加密行情、用真实盘口数据校准执行冲击模型。

## 免责声明

> 本仓库全部内容为对 Kairos 系列**真实数据历史实验结果**的研究性综合，所有数字均引自各源仓库已提交的产物文件并标注来源。全部结论仅描述特定样本内的历史统计特征，**不代表未来收益，不构成任何投资建议**。数据为公开行情、版权归原作者/数据源所有，仅在研究、学习、演示目的下少量引用，不用于任何商业用途。

> 相关笔记：数据口径见 [09-data-methodology.md](09-data-methodology.md)；过拟合打折见 [05-risk-tail.md](05-risk-tail.md)；样本外验证见 [06-strategy-robustness.md](06-strategy-robustness.md)。
