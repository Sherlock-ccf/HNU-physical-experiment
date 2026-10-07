# -*- coding: utf-8 -*-
"""
弗兰克-赫兹实验 数据处理与作图
数据来源: data.xlsx
输出:
    fig1_manual_IA_VG2K.png   手动测量 IA—VG2K 曲线
    fig2_auto_N_VG2K.png      自动测量 N—VG2K 线性拟合
    fig3_manual_N_VG2K.png    手动测量 N—VG2K 线性拟合
    _results.txt              拟合与不确定度结果
    _tables.md                原始数据表 / 峰谷表 (markdown)
"""
import numpy as np
import pandas as pd
import openpyxl
from scipy.signal import find_peaks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------- 中文字体 ----------------
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

U_B = 0.01 / np.sqrt(3.0)          # 电压表 B 类不确定度 (均匀分布), V

# ---------------- 读取数据 ----------------
df = pd.read_excel("data.xlsx", header=None)
R = df.iloc[3:168, :]               # 第 4~168 行 = 数据行 (VG2K 0~82 V)
V1 = R.iloc[:, 0].astype(float).values      # A 列
I1 = R.iloc[:, 1].astype(float).values      # B 列  手动测量1 (VF1=2.6V)
V2 = R.iloc[:, 4].astype(float).values      # E 列
I2 = R.iloc[:, 5].astype(float).values      # F 列  手动测量2 (VF2=2.2V)

wb = openpyxl.load_workbook("data.xlsx", data_only=True)
ws = wb["Sheet1"]

def row_nums(r):
    """取某一行 L~Q 列的数值"""
    out = []
    for c in range(12, 18):
        v = ws.cell(row=r, column=c).value
        if isinstance(v, (int, float)):
            out.append(float(v))
    return np.array(out)

auto = {
    "VF1=2.6V": {
        "peak_V": row_nums(3), "peak_I": row_nums(4),
        "valley_V": row_nums(5), "valley_I": row_nums(6),
    },
    "VF2=2.2V": {
        "peak_V": row_nums(7), "peak_I": row_nums(8),
        "valley_V": row_nums(9), "valley_I": row_nums(10),
    },
}

# ---------------- 线性拟合 ----------------
def linfit(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = len(x)
    xb, yb = x.mean(), y.mean()
    sxx = np.sum((x - xb) ** 2)
    sxy = np.sum((x - xb) * (y - yb))
    k = sxy / sxx
    b = yb - k * xb
    yh = k * x + b
    ssres = np.sum((y - yh) ** 2)
    sstot = np.sum((y - yb) ** 2)
    r2 = 1 - ssres / sstot if sstot > 0 else 0.0
    s = np.sqrt(ssres / (n - 2)) if n > 2 else 0.0
    uA = s / np.sqrt(sxx) if n > 2 else 0.0     # 回归散布(A类)
    uB = U_B / np.sqrt(sxx)                     # 电压表(B类)
    u = np.hypot(uA, uB)
    return dict(n=n, k=k, b=b, r2=r2, ssres=ssres, sxx=sxx, s=s, uA=uA, uB=uB, u=u)

def avg_spacing(v):
    v = np.asarray(v, float)
    d = np.diff(v)
    return d.mean(), d.std(ddof=1), d

# ---------------- 手动: 峰/谷识别 ----------------
def find_pv(V, I, prom=0.05, dist=15):
    pk, _ = find_peaks(I, prominence=prom, distance=dist)
    vl, _ = find_peaks(-I, prominence=prom, distance=dist)
    return V[pk], I[pk], V[vl], I[vl]

Vp1, Ip1, Vv1, Iv1 = find_pv(V1, I1)
Vp2, Ip2, Vv2, Iv2 = find_pv(V2, I2)

res = []
def P(s=""):
    res.append(str(s))

P("=" * 66)
P("弗兰克-赫兹实验 数据处理结果")
P("=" * 66)
P(f"电压表 B 类不确定度  u_B = 0.01/√3 = {U_B:.5f} V (均匀分布)")
P("")

# -------- 手动测量 --------
P("-" * 66)
P("[手动测量] 峰值/谷值位置 (由 IA—VG2K 曲线识别)")
P("-" * 66)
P(f"手动1 (VF1=2.6V) 峰值 VG2K: " + ", ".join(f"{v:g}" for v in Vp1))
P(f"                  峰值 IA  : " + ", ".join(f"{v:g}" for v in Ip1))
P(f"手动1 (VF1=2.6V) 谷值 VG2K: " + ", ".join(f"{v:g}" for v in Vv1))
P(f"手动2 (VF2=2.2V) 峰值 VG2K: " + ", ".join(f"{v:g}" for v in Vp2))
P(f"手动2 (VF2=2.2V) 谷值 VG2K: " + ", ".join(f"{v:g}" for v in Vv2))
P("")

manual_fits = {}
for tag, Vp, Vv in [("手动1 (VF1=2.6V)", Vp1, Vv1), ("手动2 (VF2=2.2V)", Vp2, Vv2)]:
    fp = linfit(np.arange(1, len(Vp) + 1), Vp)
    fv = linfit(np.arange(1, len(Vv) + 1), Vv)
    mp, sp, dp = avg_spacing(Vp)
    mv, sv, dv = avg_spacing(Vv)
    manual_fits[tag] = dict(peak=fp, valley=fv)
    P(f"[{tag}]")
    P(f"  峰值: 相邻峰值电压差 = " + ", ".join(f"{d:g}" for d in dp))
    P(f"        平均间距 = {mp:.3f} V,  标准差 = {sp:.3f} V")
    P(f"  N—VG2K 线性拟合(峰值): VG2K = {fp['k']:.3f}·N + {fp['b']:.3f}  "
      f"(r²={fp['r2']:.6f}, R={np.sqrt(fp['r2']):.6f})")
    P(f"        → 第一激发电位 U0 = {fp['k']:.3f} V")
    P(f"          u_A={fp['uA']:.4f} V  u_B={fp['uB']:.4f} V  u={fp['u']:.4f} V")
    P(f"        接触电势 V_c = {fp['b']:.3f} V")
    P(f"  谷值: 相邻谷值电压差 = " + ", ".join(f"{d:g}" for d in dv))
    P(f"        平均间距 = {mv:.3f} V,  标准差 = {sv:.3f} V")
    P(f"  N—VG2K 线性拟合(谷值): VG2K = {fv['k']:.3f}·N + {fv['b']:.3f}  "
      f"(r²={fv['r2']:.6f})")
    P(f"        → 第一激发电位 U0 = {fv['k']:.3f} V")
    P(f"          u_A={fv['uA']:.4f} V  u_B={fv['uB']:.4f} V  u={fv['u']:.4f} V")
    P("")

# -------- 自动测量 --------
P("-" * 66)
P("[自动测量] N—VG2K 线性拟合")
P("-" * 66)
auto_fits = {}
for tag, d in auto.items():
    fp = linfit(np.arange(1, len(d["peak_V"]) + 1), d["peak_V"])
    fv = linfit(np.arange(1, len(d["valley_V"]) + 1), d["valley_V"])
    auto_fits[tag] = dict(peak=fp, valley=fv)
    P(f"[{tag}]")
    P(f"  峰值 VG2K: " + ", ".join(f"{v:g}" for v in d["peak_V"]))
    P(f"  峰值间距 : " + ", ".join(f"{x:g}" for x in np.diff(d["peak_V"]))
      + f"   平均 {np.diff(d['peak_V']).mean():.3f} V")
    P(f"  波谷 VG2K: " + ", ".join(f"{v:g}" for v in d["valley_V"]))
    P(f"  谷值间距 : " + ", ".join(f"{x:g}" for x in np.diff(d["valley_V"]))
      + f"   平均 {np.diff(d['valley_V']).mean():.3f} V")
    P(f"  拟合(峰值): VG2K = {fp['k']:.3f}·N + {fp['b']:.3f}  r²={fp['r2']:.6f}")
    P(f"    → U0 = {fp['k']:.3f} V,  u_A={fp['uA']:.4f}  u_B={fp['uB']:.4f}  "
      f"u={fp['u']:.4f} V,  V_c={fp['b']:.3f} V")
    P(f"  拟合(谷值): VG2K = {fv['k']:.3f}·N + {fv['b']:.3f}  r²={fv['r2']:.6f}")
    P(f"    → U0 = {fv['k']:.3f} V,  u_A={fv['uA']:.4f}  u_B={fv['uB']:.4f}  "
      f"u={fv['u']:.4f} V,  V_c={fv['b']:.3f} V")
    P("")

# -------- 汇总 --------
vals = []
for tag in auto_fits:
    vals += [auto_fits[tag]["peak"]["k"], auto_fits[tag]["valley"]["k"]]
for tag in manual_fits:
    vals += [manual_fits[tag]["peak"]["k"], manual_fits[tag]["valley"]["k"]]
vals = np.array(vals)
U0_auto = np.mean([auto_fits[t]["peak"]["k"] for t in auto_fits]
                  + [auto_fits[t]["valley"]["k"] for t in auto_fits])
U0_manual = np.mean([manual_fits[t]["peak"]["k"] for t in manual_fits]
                    + [manual_fits[t]["valley"]["k"] for t in manual_fits])
REF = 11.55
P("=" * 66)
P(f"自动测量 平均 U0 = {U0_auto:.3f} V   相对公认值 {REF} V 偏差 "
  f"{abs(U0_auto-REF)/REF*100:.2f}%")
P(f"手动测量 平均 U0 = {U0_manual:.3f} V   相对公认值 {REF} V 偏差 "
  f"{abs(U0_manual-REF)/REF*100:.2f}%")
P(f"全部拟合结果范围: {vals.min():.3f} ~ {vals.max():.3f} V, 平均 {vals.mean():.3f} V")
P("=" * 66)

open("_results.txt", "w", encoding="utf-8").write("\n".join(res))
print("results written")

# ================= 作图 =================
# ---------- 图1: 手动测量 IA—VG2K ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
for ax, (V, I, Vp, Ip, Vv, Iv, tag) in zip(axes, [
        (V1, I1, Vp1, Ip1, Vv1, Iv1, "(a) VF1 = 2.6 V"),
        (V2, I2, Vp2, Ip2, Vv2, Iv2, "(b) VF2 = 2.2 V")]):
    ax.plot(V, I, "-", color="#1f4e79", lw=1.6, label="IA—VG2K 曲线")
    ax.plot(Vp, Ip, "o", ms=6, mfc="none", mec="crimson", mew=1.8, label="波峰")
    ax.plot(Vv, Iv, "^", ms=7, mfc="none", mec="seagreen", mew=1.8, label="波谷")
    for x, y in zip(Vp, Ip):
        ax.annotate(f"{x:g}", (x, y), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=8, color="crimson")
    ax.set_xlabel("加速电压 VG2K / V")
    ax.set_ylabel("板极电流 IA / $10^{-7}$A")
    ax.set_title(tag)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
fig.suptitle("图1  手动测量 IA—VG2K 曲线", fontsize=14)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig("fig1_manual_IA_VG2K.png", dpi=200)
plt.close(fig)

# ---------- 图2: 自动测量 N—VG2K ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
for ax, (tag, d) in zip(axes, auto.items()):
    Np = np.arange(1, len(d["peak_V"]) + 1)
    Nv = np.arange(1, len(d["valley_V"]) + 1)
    fp = auto_fits[tag]["peak"]; fv = auto_fits[tag]["valley"]
    ax.plot(Np, d["peak_V"], "o", ms=7, color="crimson", label="波峰")
    ax.plot(Nv, d["valley_V"], "^", ms=8, color="seagreen", label="波谷")
    xx = np.linspace(0.6, len(d["peak_V"]) + 0.4, 50)
    ax.plot(xx, fp["k"] * xx + fp["b"], "-", color="crimson", lw=1.4, alpha=0.8,
            label=f"波峰拟合  U0={fp['k']:.2f} V (r²={fp['r2']:.4f})")
    ax.plot(xx, fv["k"] * xx + fv["b"], "--", color="seagreen", lw=1.4, alpha=0.8,
            label=f"波谷拟合  U0={fv['k']:.2f} V (r²={fv['r2']:.4f})")
    ax.set_xlabel("波峰/波谷序号 N")
    ax.set_ylabel("加速电压 VG2K / V")
    ax.set_title(f"{tag}")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
fig.suptitle("图2  自动测量 N—VG2K 曲线及线性拟合", fontsize=14)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig("fig2_auto_N_VG2K.png", dpi=200)
plt.close(fig)

# ---------- 图3: 手动测量 N—VG2K ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
for ax, (Vp, Vv, tag) in zip(axes, [
        (Vp1, Vv1, "(a) VF1 = 2.6 V"),
        (Vp2, Vv2, "(b) VF2 = 2.2 V")]):
    Np = np.arange(1, len(Vp) + 1)
    Nv = np.arange(1, len(Vv) + 1)
    fp = linfit(Np, Vp); fv = linfit(Nv, Vv)
    ax.plot(Np, Vp, "o", ms=7, color="crimson", label="波峰")
    ax.plot(Nv, Vv, "^", ms=8, color="seagreen", label="波谷")
    xx = np.linspace(0.6, len(Vp) + 0.4, 50)
    ax.plot(xx, fp["k"] * xx + fp["b"], "-", color="crimson", lw=1.4, alpha=0.8,
            label=f"波峰拟合  U0={fp['k']:.2f} V (r²={fp['r2']:.4f})")
    ax.plot(xx, fv["k"] * xx + fv["b"], "--", color="seagreen", lw=1.4, alpha=0.8,
            label=f"波谷拟合  U0={fv['k']:.2f} V (r²={fv['r2']:.4f})")
    ax.set_xlabel("波峰/波谷序号 N")
    ax.set_ylabel("加速电压 VG2K / V")
    ax.set_title(tag)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
fig.suptitle("图3  手动测量 N—VG2K 曲线及线性拟合", fontsize=14)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig("fig3_manual_N_VG2K.png", dpi=200)
plt.close(fig)

# ================= 导出表格 =================
L = []
L.append("### 表1  手动测量原始数据（VG2K—IA）\n")
L.append("| VG2K/V | IA/10⁻⁷A (VF1=2.6V) | IA/10⁻⁷A (VF2=2.2V) |")
L.append("|---:|---:|---:|")
for a, b, c in zip(V1, I1, I2):
    L.append(f"| {a:g} | {b:g} | {c:g} |")
L.append("")

L.append("### 表2  手动测量峰谷位置\n")
L.append("| 手动测量1 (VF1=2.6V) | | 手动测量2 (VF2=2.2V) | |")
L.append("|:--|--:|:--|--:|")
L.append("| 波峰 VG2K/V | IA | 波峰 VG2K/V | IA |")
for i in range(max(len(Vp1), len(Vp2))):
    a = f"{Vp1[i]:g}" if i < len(Vp1) else ""
    b = f"{Ip1[i]:g}" if i < len(Ip1) else ""
    c = f"{Vp2[i]:g}" if i < len(Vp2) else ""
    d = f"{Ip2[i]:g}" if i < len(Ip2) else ""
    L.append(f"| {a} | {b} | {c} | {d} |")
L.append("| 波谷 VG2K/V | IA | 波谷 VG2K/V | IA |")
for i in range(max(len(Vv1), len(Vv2))):
    a = f"{Vv1[i]:g}" if i < len(Vv1) else ""
    b = f"{Iv1[i]:g}" if i < len(Iv1) else ""
    c = f"{Vv2[i]:g}" if i < len(Vv2) else ""
    d = f"{Iv2[i]:g}" if i < len(Iv2) else ""
    L.append(f"| {a} | {b} | {c} | {d} |")
L.append("")

L.append("### 表3  自动测量波峰数据\n")
L.append("| 序号 | VF1=2.6V VG2K/V | IA/10⁻⁷A | VF2=2.2V VG2K/V | IA/10⁻⁷A |")
L.append("|:-:|--:|--:|--:|--:|")
for i in range(6):
    L.append(f"| {i+1} | {auto['VF1=2.6V']['peak_V'][i]:g} | {auto['VF1=2.6V']['peak_I'][i]:g} "
             f"| {auto['VF2=2.2V']['peak_V'][i]:g} | {auto['VF2=2.2V']['peak_I'][i]:g} |")
L.append("")

L.append("### 表4  自动测量波谷数据\n")
L.append("| 序号 | VF1=2.6V VG2K/V | IA/10⁻⁷A | VF2=2.2V VG2K/V | IA/10⁻⁷A |")
L.append("|:-:|--:|--:|--:|--:|")
for i in range(5):
    L.append(f"| {i+1} | {auto['VF1=2.6V']['valley_V'][i]:g} | {auto['VF1=2.6V']['valley_I'][i]:g} "
             f"| {auto['VF2=2.2V']['valley_V'][i]:g} | {auto['VF2=2.2V']['valley_I'][i]:g} |")
L.append("")
open("_tables.md", "w", encoding="utf-8").write("\n".join(L))
print("tables written; figures saved")
