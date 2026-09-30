# 01 · 该 A 股池的异象 / 因子图谱

> 问题：在这 38 只大盘蓝筹上，动量还是反转？低波动异象存在吗？信号有多少其实是行业 beta？IC 到底显不显著？
> 数据：`kairos-factor` 真实 A 股因子研究（h=5 日、5 分层、多空 Q5−Q1、等权无成本）+ `kairos-ml` 裸因子样本外 IC 对照 + `kairos-risk` 因子风险分解。

## 背景 / 问题

业界常用「|秩 IC| ≥ 0.03 且非重叠 |t| ≥ 2」作为单因子可用的门槛。本篇用真实数据逐条检验该 A 股池是否存在达标的异象，并刻画动量/反转的**期限结构**、低波动异象、以及信号里**行业 beta 的占比**。

## 数据与方法

- 4 个因子：`momentum_60`（3 个月相对涨幅）、`momentum_20`（1 个月）、`reversal_5`（负 5 日涨幅）、`lowvol_20`（负 20 日已实现波动） (来源: kairos-factor/research/real_factor/REPORT.md)。
- 2 套预处理（raw=winsorize+zscore；neutral=+行业中性化，8 个行业哑变量 OLS 取残差）× 2 个样本（clean/full，本池中两样本标的相同）= **16 个组合** (来源: kairos-factor/research/real_factor/factor_ic.csv)。
- t 值双口径：重叠（每日 IC，窗口重叠 5 日、有自相关）与**非重叠**（每 5 日取一个 IC，更接近真实显著性） (来源: kairos-factor/research/real_factor/REPORT.md)。

## 结果

### 1. 动量 vs 反转：分期限看，没有单一答案

跨 4 个（样本×预处理）组合的秩 IC 均值与方向一致性 (来源: kairos-factor/research/real_factor/REPORT.md 第 5 节)：

| 因子 | 秩 IC 均值 | 同号组合数 | 判定 |
|---|---|---|---|
| `momentum_60`（3 个月） | **-0.0044** | 4/4 负 | 3 个月**反转**（量级可忽略） |
| `momentum_20`（1 个月） | **+0.0131** | 4/4 正 | 1 个月**动量**延续 |
| `reversal_5`（5 日） | +0.0006 | 2/4 混合 | 无稳定方向 |
| `lowvol_20` | +0.0012 | 2/4 混合 | 无稳定方向 |

主样本 clean·raw 的秩 IC：momentum_60 **-0.0082**、momentum_20 **+0.0161**、reversal_5 -0.0015、lowvol_20 +0.0065 (来源: kairos-factor/research/real_factor/factor_ic.csv)。

> 该池呈现**极短期反转、一个月动量、三个月再反转**的混合结构，而非单纯的动量市或反转市。若必须二选一，以 3 个月口径看整体略偏**反转**，但量级扣成本后无实用价值 (来源: kairos-factor/research/real_factor/REPORT.md)。

`momentum_20` 的秩 IC 衰减在 h=10 日见顶（clean·raw：h1 -0.0002 → h2 +0.0085 → h5 +0.0161 → **h10 +0.0204** → h20 +0.0113），说明一个月动量的信息在约两周持有期内最充分 (来源: kairos-factor/research/real_factor/factor_ic.csv)。

### 2. IC 显著性：稳健口径下 0 个达标

- 16 个组合中，**最大 |秩 IC| 仅 0.0161**（clean·momentum_20·raw），低于 0.03~0.05 的可用门槛 (来源: kairos-factor/research/real_factor/REPORT.md)。
- 重叠口径下 |t| ≥ 2 的有 4 个（全部是 momentum_20，如 clean·raw t=2.646）；但**修正重叠自相关后（非重叠抽样）|t| ≥ 2 的有 0 个**——没有一个组合能在稳健口径下通过显著性检验 (来源: kairos-factor/research/real_factor/REPORT.md；factor_ic.csv `rank_ic_t` vs `rank_ic_t_nonoverlap`)。
- 分层单调性（neutral，5 层收益与组序的 spearman）：momentum_60 **+0.90**、momentum_20 **+0.90**、lowvol_20 **-0.90** 近似单调；reversal_5 仅 +0.30（非单调） (来源: kairos-factor/research/real_factor/REPORT.md)。

### 3. 低波动异象：factor 与 ml 给出**不同口径下的张力**

- **factor 全样本（无成本、重叠）**：`lowvol_20` 判定「无稳定方向」，秩 IC 随预处理翻号（clean·raw +0.0065 / clean·neutral -0.0041），多空 -43.9 / -40.2 bp/期；但分层呈**低波动组收益更高**的单调形态（clean·neutral：Q1 最低波动 +58.2bp → Q5 +18.0bp，spearman -0.90） (来源: kairos-factor/research/real_factor/factor_ic.csv、quantile_returns.csv)。
- **ml 严格样本外（日频截面 IC）**：把波动率特征直接当打分，`rv10`（10 日已实现波动）IC = **-0.03963**（t=**-5.00**）、`rv20` IC = **-0.03352**（t=**-4.00**）——负 IC 意味着「做多低波动、做空高波动」，正是经典**低波动异象**，且是全表 |t| 最大的打分 (来源: kairos-ml/research/real_ml/metrics.json `diagnostics.factor_ic`)。

> 诚实解读：两个仓库并不矛盾，而是**口径不同**。factor 的秩 IC 是全样本、含重叠、以 5 日远期收益配对，量级被噪声淹没故判「不稳定」；ml 的裸因子 IC 是严格样本外、日频、1426 个截面日，把低波动信号测出了 t=-5.00 的显著性。**低波动是本池唯一在样本外稳健显著的异象**，但它的强度不足以单独覆盖成本（见 [02-ml-vs-factor.md](02-ml-vs-factor.md)）。

### 4. 行业 beta 占比：中性化削掉的近一半是行业行情

- 行业中性化后，主样本平均 |秩 IC| 由 **0.0081（raw）降到 0.0043（neutral）**，降幅 **46%**；4/4 个因子的多空价差绝对值都下降 (来源: kairos-factor/research/real_factor/REPORT.md)。说明原始信号相当一部分来自行业间涨跌差异（新能源/白酒/银行/券商的板块行情），而非纯个股选择能力。
- 从风险侧印证：等权市场代理一个因子就解释了组合方差的 **94.58%**，个股单因子 R² 中位 **0.316**、beta 中位 1.036 (来源: kairos-risk/research/real_risk/risk_metrics.json `factor`)。即在这篮子高相关蓝筹里，**行业/市场 beta 是收益与波动的主因**，特质 alpha 空间很小。

## 解读

该 A 股池的因子图谱可以概括为：**「弱动量（1 个月）+ 弱反转（3 个月）+ 一个样本外稳健但幅度不足的低波动异象 + 大部分方差是市场 beta」**。方向最一致的是 momentum_20（4/4 正），但非重叠 |t| 最大仅 1.50，达不到实盘门槛；最值得记住的是低波动（rv10 样本外 t=-5.00），它也是后续 ML 篇里「模型反而稀释掉的有效信号」(来源: kairos-ml/research/real_ml/REPORT.md)。

## 局限 / 后续

- 38 只、单层约 8 只，截面统计噪声大，IC 标准误与信号量级相当 (来源: kairos-factor/research/real_factor/REPORT.md)。
- 一次检验 16 个组合，5% 水平上本就期望约 1 个「假显著」，单看 t 值极易过拟合；未做多重检验校正。
- 多空价差**未扣交易成本**，5 日调仓的单边换手会让价差大幅缩水。
- 后续：扩样本、加成交量/基本面字段、对低波动异象单独做含成本与容量约束的可投资性检验。

> 相关笔记：低波动信号在 ML 里被稀释的机制见 [02-ml-vs-factor.md](02-ml-vs-factor.md)；市场 beta 主导的风险分解见 [05-risk-tail.md](05-risk-tail.md)。
