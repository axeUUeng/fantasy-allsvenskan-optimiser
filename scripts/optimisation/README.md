<!-- MathJax setup for GitHub Pages rendering -->
<script type="text/javascript"
  async
  src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.js">
</script>

# Optimisation Scripts

Tools for selecting the best fantasy squad given the current constraints.

- **optimize_team.py** – interactive team optimiser using CVXPY.
- **OLD_optimize_team.py** – previous iteration kept for reference.
- **test_quest.py** – small experiment with command-line prompts.

## Problem Formulation

The optimiser chooses a 15 player squad that maximises projected points subject
to Fantasy Allsvenskan rules.

Let $P$ be the set of all available players and $T$ the set of clubs. For each
player $i \in P$ we know:

- $c_i$ – player cost  
- $e_i$ – expected points forecast  
- $m_i$ – market score  
- $u_i$ – upside score  
- $d_i$ – discipline penalty  
- $t(i) \in T$ – club the player belongs to  
- $\text{pos}(i)$ – position (GK/DEF/MID/FWD)  
- $ch_i \in \{0,1\}$ – indicator if $i$ is a transfer  

Decision variable $x_i \in \{0,1\}$ indicates whether player $i$ is selected.  
If $B$ is the available budget and $\lambda$ the transfer penalty weight, the
problem is:

$$
\begin{aligned}
\max_x\; & \sum_{i\in P} (e_i + 0.008 m_i + 0.006 u_i - 0.005 d_i) \cdot x_i \\
         &- \lambda \sum_{i\in P} ch_i x_i \\
\text{s.t.}\;\; 
         & \sum_{i\in P} c_i x_i \le B, \\
         & \sum_{i\in P} x_i = 15, \\
         & \sum_{i:\text{pos}(i)=\mathrm{GK}} x_i = 2, \\
         & \sum_{i:\text{pos}(i)=\mathrm{DEF}} x_i = 5, \\
         & \sum_{i:\text{pos}(i)=\mathrm{MID}} x_i = 5, \\
         & \sum_{i:\text{pos}(i)=\mathrm{FWD}} x_i = 3, \\
         & \sum_{i:\; t(i)=t} x_i \le 3 \quad \forall t \in T, \\
         & \sum_{i\in P} ch_i x_i \le \text{MAX\_TRANSFERS} \;\text{(optional)}, \\
         & x_i \in \{0,1\} \quad \forall i \in P.
\end{aligned}
$$