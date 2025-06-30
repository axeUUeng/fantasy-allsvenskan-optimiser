# Optimisation Scripts

Tools for selecting the best Fantasy Allsvenskan squad given the current constraints.

### Files

* **`optimize_team.py`** – Interactive team optimiser using CVXPY.
* **`OLD_optimize_team.py`** – Previous iteration kept for reference.
* **`test_quest.py`** – Small experiment with command-line prompts.

---

## Problem Formulation

The optimiser selects a 15-player squad that maximises projected points, subject to Fantasy Allsvenskan rules.

Let $P$ be the set of all available players and $T$ the set of clubs. For each player $i \in P$, we know:

* $c\_i$ – player cost
* $e\_i$ – expected points forecast
* $m\_i$ – market score
* $u\_i$ – upside score
* $d\_i$ – discipline penalty
* $t(i) \in T$ – club the player belongs to
* $\text{pos}(i)$ – position (GK/DEF/MID/FWD)
* $ch\_i \in {0, 1}$ – indicator if $i$ is a transfer

We define a decision variable:

* $x\_i \in {0, 1}$ – whether player $i$ is selected

Let $B$ be the available budget, and $\lambda$ a transfer penalty weight. The optimisation problem is:

```math
\begin{aligned}
\max_x\quad & \sum_{i\in P} (e_i + 0.008 m_i + 0.006 u_i - 0.005 d_i)\, x_i 
             - \lambda \sum_{i\in P} ch_i x_i \\
\text{s.t.}\quad 
            & \sum_{i\in P} c_i x_i \le B \\
            & \sum_{i\in P} x_i = 15 \\
            & \sum_{i:\text{pos}(i)=\mathrm{GK}} x_i = 2 \\
            & \sum_{i:\text{pos}(i)=\mathrm{DEF}} x_i = 5 \\
            & \sum_{i:\text{pos}(i)=\mathrm{MID}} x_i = 5 \\
            & \sum_{i:\text{pos}(i)=\mathrm{FWD}} x_i = 3 \\
            & \sum_{i:\ t(i)=t} x_i \le 3 \quad \forall t \in T \\
            & \sum_{i\in P} ch_i x_i \le \text{MAX\_TRANSFERS} \quad \text{(optional)} \\
            & x_i \in \{0,1\} \quad \forall i \in P
\end{aligned}
```
