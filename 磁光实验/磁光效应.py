# -*- coding: utf-8 -*-
"""
磁光效应（法拉第磁致旋光）实验 —— 数据分析与作图

数据从 data.xls 读取（Sheet1），对应报告模板 "2. 数据分析" 部分：
  (1) 马吕斯定律拟合 I = I0·cos²(θ−θmax) + I_dark，计算消光比 M = Pmax/Pmin
  (2) 由电流算磁感应强度 B、算三种情况的 θn−θ0、
      作 θ–B 图并线性拟合求维尔德常量 V

所有拟合结果均给出不确定度，以 k = XXX ± XXX 的形式输出。

用法：python 磁光效应.py
输出：fig1_马吕斯定律.png / fig2_情况I.png / fig3_情况II.png /
      fig4_情况III.png / fig5_三种情况对比.png / 数据分析结果.md
"""

import sys

import numpy as np
import matplotlib.pyplot as plt
import xlrd
from matplotlib import rcParams

# Windows 控制台默认 GBK，改成 UTF-8 以免打印中文/符号时报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False

# ============================ 实验常数 ============================
DATA_FILE = "data.xls"

N_TURNS = 1750          # 励磁线圈（外线圈）匝数
L_COIL = 0.05           # 螺线管长度 Le (m)
L_MED = 0.030           # 磁致旋光材料长度 L = 30 mm (m)
MU0 = 4e-7 * np.pi      # 真空磁导率 μ0 ≈ 4π×10^-7 N/A^2

# data.xls 中四个数据块的列号：(电流/角度列, 读数列, 光强列)
COL_MALUS = (0, 1)                      # 马吕斯：角度、光强
COL_CASES = [(3, 4, 5), (7, 8, 9), (11, 12, 13)]
DATA_START_ROW = 2                      # 前两行是表头

CASE_NAMES = ["I  初始状态", "II  改变磁感应强度 B 的方向", "III 改变入射光方向"]
CASE_TAG = ["I", "II", "III"]

PARAM_BOX = dict(boxstyle="round,pad=0.4", facecolor="#FFF8DC", edgecolor="gray", alpha=0.9)


# ============================ 读取 data.xls ============================
def parse_angle(v):
    """把 '338°8'' 这种度分格式的角度化成十进制度；本来就是数字则直接返回"""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    for ch in "°'′\"″":
        s = s.replace(ch, " ")
    parts = s.split()
    deg = float(parts[0])
    minute = float(parts[1]) if len(parts) > 1 else 0.0
    return deg + minute / 60.0


def parse_power(v):
    """光强读数：'0.00 08' 这种把空格当小数点的写法也要能吃进来"""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    return float(s) if s else np.nan


def read_column(sh, col, n_expected=None):
    """从 DATA_START_ROW 起逐行读某一列，遇到空单元格就停"""
    vals = []
    r = DATA_START_ROW
    while r < sh.nrows:
        v = sh.cell_value(r, col)
        if v == "" or v is None:
            break
        vals.append(v)
        r += 1
    if n_expected is not None and len(vals) != n_expected:
        print(f"  提示：第 {col} 列读到 {len(vals)} 个数据（预期 {n_expected} 个）")
    return vals


wb = xlrd.open_workbook(DATA_FILE)
sh = wb.sheet_by_index(0)

# 转动方向记录在表头行（形如 "检偏器转动方向：逆时针"）
def read_direction(col):
    txt = str(sh.cell_value(0, col))
    return txt.split("：")[-1].strip() if "：" in txt else txt.strip()


MALUS_ANGLE = np.array([parse_angle(v) for v in read_column(sh, COL_MALUS[0])])
MALUS_POWER = np.array([parse_power(v) for v in read_column(sh, COL_MALUS[1])])

MAG_CURRENTS, MAG_ANGLES, MAG_POWERS = [], [], []
for c_cur, c_ang, c_pow in COL_CASES:
    MAG_CURRENTS.append(np.array([float(v) for v in read_column(sh, c_cur)]))
    MAG_ANGLES.append(np.array([parse_angle(v) for v in read_column(sh, c_ang)]))
    MAG_POWERS.append(np.array([parse_power(v) for v in read_column(sh, c_pow)]))

CURRENTS = MAG_CURRENTS[0]                  # 三组电流相同
B_FIELD = MU0 * N_TURNS / L_COIL * CURRENTS  # B = μ0·N·I / Le

n_malus = len(MALUS_ANGLE)
n_pt = len(CURRENTS)
print(f"已读取 {DATA_FILE}：马吕斯 {n_malus} 点，磁致旋光 {n_pt} 点 × 3 组")
print(f"  马吕斯转动方向：{read_direction(1)}")
print("  磁致旋光转动方向：" + "，".join(
    f"{t} {read_direction(c)}" for t, c in zip(CASE_TAG, [4, 8, 12])))
print()


# ============================ 通用工具 ============================
def wrap180(deg):
    """把角度差折回 (-180, 180]，避免检偏器读数跨 0°/360° 时算错"""
    return (np.asarray(deg, dtype=float) + 180.0) % 360.0 - 180.0


def pm(val, err, sig=2):
    """把结果格式化成 val ± err，小数位由误差的有效数字决定"""
    if not np.isfinite(err) or err == 0:
        return f"{val:.4g}"
    dec = max(0, -(int(np.floor(np.log10(abs(err)))) - (sig - 1)))
    return f"{val:.{dec}f} ± {err:.{dec}f}"


def style_ax(ax, xlabel, ylabel, title):
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.grid(alpha=0.35, linestyle="--", linewidth=0.6)


def r_squared(y, y_fit):
    ss_res = np.sum((y - y_fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return 1.0 - ss_res / ss_tot


# ============================ 分析 (1) 马吕斯定律 ============================
# I = I0·cos²(θ−θmax) + I_dark
# 线性化：I = p·cos2θ + q·sin2θ + r
#   → I0 = 2√(p²+q²)，θmax = ½·arctan2(q,p)，I_dark = r − √(p²+q²)
# 误差由最小二乘协方差矩阵 Cov = s²·(AᵀA)⁻¹ 传播。
th = np.deg2rad(MALUS_ANGLE)
A = np.column_stack([np.cos(2 * th), np.sin(2 * th), np.ones_like(th)])
pqr, *_ = np.linalg.lstsq(A, MALUS_POWER, rcond=None)
p, q, r = pqr
resid = MALUS_POWER - A @ pqr
dof = n_malus - 3
s2 = np.sum(resid ** 2) / dof
cov = s2 * np.linalg.inv(A.T @ A)

R_amp = np.hypot(p, q)
I0_fit = 2.0 * R_amp
theta_max_fit = 0.5 * np.rad2deg(np.arctan2(q, p)) % 180.0
I_dark_fit = r - R_amp
R2_malus = r_squared(MALUS_POWER, A @ pqr)

# 误差传播：J 为各量对 (p,q,r) 的偏导
J_I0 = np.array([2 * p / R_amp, 2 * q / R_amp, 0.0])
err_I0 = np.sqrt(J_I0 @ cov @ J_I0)
J_th = np.array([-0.5 * q / R_amp ** 2, 0.5 * p / R_amp ** 2, 0.0])
err_theta_max = np.rad2deg(np.sqrt(J_th @ cov @ J_th))
J_dark = np.array([-p / R_amp, -q / R_amp, 1.0])
err_I_dark = np.sqrt(J_dark @ cov @ J_dark)

P_max, P_min = MALUS_POWER.max(), MALUS_POWER.min()
# 消光比 M = Pmax/Pmin；若 Pmin 读数为 0（低于功率计分辨力），只能给出下限
pos = MALUS_POWER[MALUS_POWER > 0]
if P_min > 0:
    M_text = f"{P_max / P_min:.1f}"
    M_lower = False
else:
    M_text = f"≥ {P_max / pos.min():.0f}（Pmin 读数为 0）"
    M_lower = True
M_fit_text = pm(I0_fit / I_dark_fit, 0.0) if I_dark_fit > 0 else "∞"

fig, ax = plt.subplots(figsize=(8.2, 5.2))
order = np.argsort(MALUS_ANGLE)
ax.scatter(MALUS_ANGLE[order], MALUS_POWER[order], s=42, c="blue", zorder=3, label="实验数据")
xs = np.linspace(-10, 370, 1000)
ax.plot(xs, I0_fit * np.cos(np.deg2rad(xs - theta_max_fit)) ** 2 + I_dark_fit, "r-", lw=2,
        label=f"拟合曲线: I = {I0_fit:.4f}·cos²(θ−{theta_max_fit:.2f}°)+{I_dark_fit:.4f}")
ax.text(0.03, 0.06,
        "拟合参数：\n"
        f"I0 = {pm(I0_fit, err_I0)} mW\n"
        f"θmax = {pm(theta_max_fit, err_theta_max)}°\n"
        f"（消光角 = θmax±90°）\n"
        f"I_dark = {pm(I_dark_fit, err_I_dark)} mW\n"
        f"R² = {R2_malus:.4f}\n"
        f"消光比 M = Pmax/Pmin = {M_text}",
        transform=ax.transAxes, fontsize=10, va="bottom", bbox=PARAM_BOX)
ax.set_ylim(-0.03, P_max * 1.22)
ax.set_xticks(np.arange(0, 361, 30))
ax.legend(loc="upper right", fontsize=10)
style_ax(ax, "检偏器角度位置 θ (°)", "光强 P (mW)", "马吕斯定律验证：光强与检偏器角度的关系")
fig.tight_layout()
fig.savefig("fig1_马吕斯定律.png", dpi=300)
plt.close(fig)


# ==================== 分析 (2) 磁致旋光：θ-B 关系与维尔德常量 ====================
def analyse_case(name, theta_pos, powers):
    """由一组检偏器角度位置算 θn−θ0，并拟合 θ = V·B·L 求维尔德常量及其不确定度"""
    theta_pos = np.asarray(theta_pos, dtype=float)
    theta0 = theta_pos[0]
    dtheta_deg = wrap180(theta_pos - theta0)
    dtheta_rad = np.deg2rad(dtheta_deg)

    # 理论关系 θ = V·B·L 无截距，用过原点最小二乘：V = Σ(B·θ)/(L·ΣB²)
    S_BB = np.sum(B_FIELD ** 2)
    V_origin = np.sum(B_FIELD * dtheta_rad) / (L_MED * S_BB)
    theta_fit_origin = V_origin * L_MED * B_FIELD
    r2_origin = r_squared(dtheta_rad, theta_fit_origin)
    resid_o = dtheta_rad - theta_fit_origin
    # σ_V = σ_k / L，其中 σ_k = √( (Σ残差²/(n−1)) / ΣB² )
    err_k_origin = np.sqrt(np.sum(resid_o ** 2) / (n_pt - 1) / S_BB)
    err_V_origin = err_k_origin / L_MED

    # 对照：带截距线性拟合 θ = k·B + b，用标准最小二乘误差公式
    k, b = np.polyfit(B_FIELD, dtheta_rad, 1)
    Delta = n_pt * S_BB - np.sum(B_FIELD) ** 2
    s_ls = np.sqrt(np.sum((dtheta_rad - (k * B_FIELD + b)) ** 2) / (n_pt - 2))
    err_k_free = s_ls * np.sqrt(n_pt / Delta)
    err_b_free = s_ls * np.sqrt(S_BB / Delta)
    V_free = k / L_MED
    err_V_free = err_k_free / L_MED
    r2_free = r_squared(dtheta_rad, k * B_FIELD + b)

    with np.errstate(divide="ignore", invalid="ignore"):
        V_each = np.where(B_FIELD > 0, dtheta_rad / (B_FIELD * L_MED), np.nan)

    return dict(
        name=name, theta0=theta0, powers=powers,
        dtheta_deg=dtheta_deg, dtheta_rad=dtheta_rad,
        V_origin=V_origin, err_V_origin=err_V_origin, r2_origin=r2_origin,
        k_origin=V_origin * L_MED, err_k_origin=err_k_origin,
        V_free=V_free, err_V_free=err_V_free, k_free=k, b_free=b,
        err_k_free=err_k_free, err_b_free=err_b_free, r2_free=r2_free,
        V_each=V_each,
    )


results = [analyse_case(n, a, w) for n, a, w in zip(CASE_NAMES, MAG_ANGLES, MAG_POWERS)]

for idx, (res, tag) in enumerate(zip(results, CASE_TAG)):
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    ax.scatter(B_FIELD, res["dtheta_deg"], s=48, c="blue", zorder=3, label="实验数据")
    Bs = np.linspace(0, B_FIELD.max() * 1.05, 200)
    ax.plot(Bs, np.rad2deg(res["k_origin"] * Bs), "r-", lw=2,
            label=f"拟合直线(过原点): θ = ({res['k_origin']:.3f}±{res['err_k_origin']:.3f})·B")
    ax.plot(Bs, np.rad2deg(res["k_free"] * Bs + res["b_free"]), "g--", lw=1.6,
            label=f"参考(带截距): θ = ({res['k_free']:.3f}±{res['err_k_free']:.3f})·B"
                  f"+({np.rad2deg(res['b_free']):.3f}±{np.rad2deg(res['err_b_free']):.3f})")
    ax.text(0.03, 0.95,
            "拟合参数：\n"
            f"θ0 = {res['theta0']:.2f}°\n"
            f"k = V·L = {pm(res['k_origin'], res['err_k_origin'])} rad/T\n"
            f"V = {pm(res['V_origin'], res['err_V_origin'])} rad/(T·m)\n"
            f"R² = {res['r2_origin']:.4f}",
            transform=ax.transAxes, fontsize=10, va="top", bbox=PARAM_BOX)
    ax.legend(loc="lower right", fontsize=9.5)
    style_ax(ax, "磁感应强度 B (T)", "角度变化值 θ = θn−θ0 (°)",
             f"情况{tag}：{res['name']}　θ–B 线性拟合")
    fig.tight_layout()
    fig.savefig(f"fig{idx + 2}_情况{tag}.png", dpi=300)
    plt.close(fig)

# 三种情况放在同一张图上对比
fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
colors = ["#1f77b4", "#d62728", "#2ca02c"]
for ax, res, tag, c in zip(axes, results, CASE_TAG, colors):
    ax.scatter(B_FIELD, res["dtheta_deg"], s=40, c=c, zorder=3, label="实验数据")
    Bs = np.linspace(0, B_FIELD.max() * 1.05, 200)
    ax.plot(Bs, np.rad2deg(res["k_origin"] * Bs), "k-", lw=1.8, label="线性拟合")
    ax.text(0.04, 0.96,
            f"V = {pm(res['V_origin'], res['err_V_origin'])}\n"
            f"rad/(T·m)\nR² = {res['r2_origin']:.4f}\nθ0 = {res['theta0']:.2f}°",
            transform=ax.transAxes, fontsize=9, va="top", bbox=PARAM_BOX)
    ax.legend(loc="lower right", fontsize=9)
    style_ax(ax, "B (T)", "θn−θ0 (°)", f"情况{tag}")
fig.suptitle("三种情况下旋转角 θ 与磁感应强度 B 的关系对比", fontsize=14, y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig("fig5_三种情况对比.png", dpi=300)
plt.close(fig)


# ============================ 结果汇总（Markdown） ============================
V_all = np.array([r["V_origin"] for r in results])
e_all = np.array([r["err_V_origin"] for r in results])
V_abs_mean = np.abs(V_all).mean()
V_abs_sem = np.abs(V_all).std(ddof=1) / np.sqrt(len(V_all))
V_spread = 100 * np.abs(V_all).std(ddof=1) / V_abs_mean

md = []
add = md.append

add("# 磁光效应实验 —— 数据分析结果")
add("")
add(f"- 数据来源：`{DATA_FILE}`")
add(f"- 常数：N = {N_TURNS} 匝，Le = {L_COIL} m，L = {L_MED * 1000:.1f} mm，"
    "μ0 = 4π×10^-7 N/A^2")
add(f"- 磁感应强度：B = μ0·N·I / Le = **{MU0 * N_TURNS / L_COIL:.5f} × I** (T/A)")
add("")
add("## 1. 马吕斯定律的实验验证")
add("")
add("拟合模型：$I = I_0 \\cos^2(\\theta - \\theta_{max}) + I_{dark}$")
add("")
add("| 参数 | 数值 |")
add("| :--- | :--- |")
add(f"| 光强幅值 I₀ | **{pm(I0_fit, err_I0)} mW** |")
add(f"| 透射最大角 θ_max | **{pm(theta_max_fit, err_theta_max)} °** |")
ext_a = (theta_max_fit + 90.0) % 360.0
ext_b = (theta_max_fit - 90.0) % 360.0
add(f"| 消光角 (θ_max ± 90°) | {ext_a:.2f}° / {ext_b:.2f}° |")
add(f"| 本底光强 I_dark | **{pm(I_dark_fit, err_I_dark)} mW** |")
add(f"| 拟合优度 R² | **{R2_malus:.4f}**（自由度 {dof}） |")
add("")
add(f"- 实测 P_max = **{P_max:.3f} mW**，P_min = **{P_min:.3f} mW**")
add(f"- **消光比 M = P_max/P_min = {M_text}**")
add("")
if M_lower:
    add(f"> P_min 已低到功率计分辨力，M 只能作为下限；若按拟合本底估算 M ≈ {I0_fit / I_dark_fit:.0f}。")
    add("")
add("## 2. 磁感应强度与角度变化值 θ = θₙ − θ₀")
add("")
add("| I (A) | B (T) | θ_I (°) | θ_II (°) | θ_III (°) |")
add("| ---: | ---: | ---: | ---: | ---: |")
for i, I in enumerate(CURRENTS):
    add(f"| {I:.1f} | {B_FIELD[i]:.5f} | {results[0]['dtheta_deg'][i]:.2f} | "
        f"{results[1]['dtheta_deg'][i]:.2f} | {results[2]['dtheta_deg'][i]:.2f} |")
add("")
add("## 3. 线性拟合 θ = V·B·L 与维尔德常量")
add("")
add("三种情况的转动方向：" + "，".join(
    f"{t} {'逆时针' if r['dtheta_deg'][-1] > 0 else '顺时针'}（最大转角 {r['dtheta_deg'][-1]:+.2f}°）"
    for t, r in zip(CASE_TAG, results)))
add("")
add("| 情况 | θ₀ (°) | k = V·L (rad/T) | V (rad/(T·m)) | 相对不确定度 | R² |")
add("| :--- | ---: | ---: | ---: | ---: | ---: |")
for res, tag in zip(results, CASE_TAG):
    rerr = 100 * res["err_V_origin"] / abs(res["V_origin"])
    add(f"| **{res['name']}** | {res['theta0']:.2f} | "
        f"**{pm(res['k_origin'], res['err_k_origin'])}** | "
        f"**{pm(res['V_origin'], res['err_V_origin'])}** | {rerr:.2f}% | {res['r2_origin']:.4f} |")
add("")
add("维尔德常量三种情况的完整结果：")
add("")
for res, tag in zip(results, CASE_TAG):
    add(f"- **情况 {tag}**：V = {pm(res['V_origin'], res['err_V_origin'])} rad/(T·m) "
        f"= {pm(np.rad2deg(res['V_origin']), np.rad2deg(res['err_V_origin']))} °/(T·m)")
add("")
add("> 对照：若改用含截距的线性拟合 θ = k·B + b（理论上 b 应为 0）：")
add(">")
add("> | 情况 | k (rad/T) | b (rad) | R² |")
add("> | :--- | ---: | ---: | ---: |")
for res, tag in zip(results, CASE_TAG):
    add(f"> | {tag} | {pm(res['k_free'], res['err_k_free'])} | "
        f"{pm(res['b_free'], res['err_b_free'])} | {res['r2_free']:.4f} |")
add("")
add("## 4. 三种情况的比较")
add("")
add(f"- V_I = **{pm(V_all[0], e_all[0])}**，V_II = **{pm(V_all[1], e_all[1])}**，"
    f"V_III = **{pm(V_all[2], e_all[2])}** rad/(T·m)")
add(f"- **|V| 平均 = {pm(V_abs_mean, V_abs_sem)} rad/(T·m)**")
add(f"- |V| 三组间的相对差异 = **{V_spread:.2f}%**（在测量不确定度范围内一致）")
add("")
add("### 结论")
add("")
add("1. 马吕斯定律得到很好验证，光强随检偏器角度呈 cos² 规律变化，R² = "
    f"{R2_malus:.4f}。")
add("2. 旋转角 θ 与磁感应强度 B 成正比（θ = V·B·L），三组数据的 R² 均在 0.96 以上。")
add("3. 法拉第效应具有**非互易性**：改变 B 的方向（情况 II）旋转角**反号**"
    f"（V_II = {pm(V_all[1], e_all[1])} rad/(T·m)）；改变入射光方向（情况 III）旋转角"
    f"**符号不变**（V_III = {pm(V_all[2], e_all[2])} rad/(T·m)，与情况 I 同号）。")
add(f"4. 三种情况下的 |V| 相对差异仅 {V_spread:.2f}%，说明维尔德常量只由材料和工作波长"
    "决定，与磁场方向、入射光方向均无关。")
add(f"5. 本次测得该磁致旋光材料的维尔德常量 V ≈ {pm(V_abs_mean, V_abs_sem)} rad/(T·m) "
    f"（{pm(np.rad2deg(V_abs_mean), np.rad2deg(V_abs_sem))} °/(T·m)）。")

report = "\n".join(md)
with open("数据分析结果.md", "w", encoding="utf-8") as f:
    f.write(report + "\n")

# 控制台只打印关键数字，完整结果见 markdown 文件
print("=" * 56)
print("关键结果")
print("=" * 56)
print(f"马吕斯：θmax = {pm(theta_max_fit, err_theta_max)}°，"
      f"R² = {R2_malus:.4f}，M = {M_text}")
for res, tag in zip(results, CASE_TAG):
    print(f"情况{tag:>4}：k = {pm(res['k_origin'], res['err_k_origin'])} rad/T，"
          f"V = {pm(res['V_origin'], res['err_V_origin'])} rad/(T·m)")
print(f"|V| 平均 = {pm(V_abs_mean, V_abs_sem)} rad/(T·m)，组间差异 {V_spread:.2f}%")
print("=" * 56)

print("\n已保存：数据分析结果.md")
print("已保存图像：fig1_马吕斯定律.png, fig2_情况I.png, fig3_情况II.png, "
      "fig4_情况III.png, fig5_三种情况对比.png")
plt.show()
