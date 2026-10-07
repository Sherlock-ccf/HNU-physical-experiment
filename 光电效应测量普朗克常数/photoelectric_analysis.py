# -*- coding: utf-8 -*-
"""
光电效应测量普朗克常数 —— 数据处理与作图
数据来源: data.xlsx
波长零点校准: lambda_c = lambda_读 - 37.6 nm  (单色仪 0.01 mm <-> 1 nm, 零点读数 0.376 mm)
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# ---------------------------------------------------------------- 常数
C_LIGHT = 2.99792458e8      # m/s
E_CHARGE = 1.602176634e-19  # C
H_TRUE = 6.62607015e-34     # J*s

# ---------------------------------------------------------------- 原始数据
DELTA_LAMBDA = -37.6        # nm, 波长零点校准值 (减)
LAM = np.array([420, 435, 450, 465, 480, 495, 510, 525, 540, 555, 570], float)
NEG_U0 = np.array([1.74, 1.65, 1.55, 1.45, 1.39, 1.30, 1.22, 1.14, 1.08, 1.01, 0.93])
ID = np.array([-1.60, -1.50, -1.50, -1.60, -1.50, -1.50, -1.60, -1.40, -1.60, -1.60, -1.60])
NEG_UD = np.array([1.83, 1.71, 1.61, 1.53, 1.47, 1.33, 1.26, 1.16, 1.10, 1.03, 0.96])

LAM_C = LAM + DELTA_LAMBDA                 # 校准后波长 / nm
NU = C_LIGHT / (LAM_C * 1e-9) / 1e14       # 频率 / 10^14 Hz
U0 = np.abs(NEG_U0)                        # 遏止电压 / V
UD = np.abs(NEG_UD)

# 电压表 B 类不确定度 (最大允许误差 0.01 V, 均匀分布)
U_B_VOLT = 0.01 / np.sqrt(3)


def linear_fit(x, y, u_b_y=U_B_VOLT):
    """一元线性最小二乘 y = k x + d, 返回斜率/截距及其 A、B 类合成不确定度。"""
    n = len(x)
    xbar, ybar = x.mean(), y.mean()
    Sxx = np.sum((x - xbar) ** 2)
    Syy = np.sum((y - ybar) ** 2)
    Sxy = np.sum((x - xbar) * (y - ybar))
    k = Sxy / Sxx
    d = ybar - k * xbar
    resid = y - (k * x + d)
    s = np.sqrt(np.sum(resid ** 2) / (n - 2))          # 剩余标准差
    uA_k = s / np.sqrt(Sxx)
    uB_k = u_b_y / np.sqrt(Sxx)
    u_k = np.hypot(uA_k, uB_k)
    uA_d = s * np.sqrt(1.0 / n + xbar ** 2 / Sxx)
    uB_d = u_b_y * np.sqrt(1.0 / n + xbar ** 2 / Sxx)
    u_d = np.hypot(uA_d, uB_d)
    r = Sxy / np.sqrt(Sxx * Syy)
    return dict(k=k, d=d, s=s, uA_k=uA_k, uB_k=uB_k, u_k=u_k,
                uA_d=uA_d, uB_d=uB_d, u_d=u_d, r=r, n=n, Sxx=Sxx)


def report(name, fit):
    k, d = fit["k"], fit["d"]
    h = E_CHARGE * k * 1e-14          # V/(10^14 Hz) -> J*s
    W = -d                            # eV  (截距单位即 V, 数值上等于 eV)
    nu0 = -d / k * 1e14               # Hz
    u_h = E_CHARGE * fit["u_k"] * 1e-14
    u_W = fit["u_d"]                  # eV
    rel_nu0 = np.hypot(fit["u_d"] / d, fit["u_k"] / k)
    print(f"\n===== {name} =====")
    print(f"  U = ({k:.6f} +/- {fit['u_k']:.6f}) nu + ({d:.6f} +/- {fit['u_d']:.6f})"
          f"   [nu 单位 1e14 Hz]")
    print(f"  r = {fit['r']:.5f}   s(剩余) = {fit['s']:.4f} V   n = {fit['n']}")
    print(f"  uA(k)={fit['uA_k']:.2e}  uB(k)={fit['uB_k']:.2e}  ->  u(k)={fit['u_k']:.2e}")
    print(f"  h  = {h:.4e} +/- {u_h:.2e} J*s   相对误差 {(h/H_TRUE-1)*100:+.2f}%")
    print(f"  W  = {W:.3f} +/- {u_W:.3f} eV")
    print(f"  nu0= {nu0:.4e} Hz  ({nu0/1e14:.3f}e14 Hz)  相对不确定度 {rel_nu0*100:.2f}%")
    return dict(k=k, d=d, u_k=fit["u_k"], u_d=fit["u_d"], r=fit["r"], s=fit["s"],
                h=h, u_h=u_h, W=W, u_W=u_W, nu0=nu0, rel_nu0=rel_nu0)


print("校准: lambda_c = lambda - 37.6 nm   零点读数 0.376 mm (=37.6 nm)")
print("lambda_c /nm :", np.array2string(LAM_C, precision=1))
print("nu /1e14 Hz  :", np.array2string(NU, precision=3))

fit0 = linear_fit(NU, U0)
fitd = linear_fit(NU, UD)
R0 = report("U0 ~ nu  (光电流为零法)", fit0)
Rd = report("Ud ~ nu  (交点/补偿法)", fitd)

# 平均结果
h_avg = (R0["h"] + Rd["h"]) / 2
W_avg = (R0["W"] + Rd["W"]) / 2
n0_avg = (R0["nu0"] + Rd["nu0"]) / 2
print(f"\n===== 平均 =====")
print(f"  h_bar = {h_avg:.4e} J*s  相对误差 {(h_avg/H_TRUE-1)*100:+.2f}%")
print(f"  W_bar = {W_avg:.3f} eV   nu0_bar = {n0_avg:.4e} Hz")


# ---------------------------------------------------------------- 作图
def draw(ax, x, y, fit, title, color, label):
    ax.scatter(x, y, s=55, color=color, zorder=3, edgecolor="white", linewidth=0.8,
               label=label)
    xs = np.linspace(x.min() - 0.15, x.max() + 0.15, 100)
    ax.plot(xs, fit["k"] * xs + fit["d"], "-", color=color, lw=1.8, zorder=2,
            label="最小二乘拟合直线")
    h = E_CHARGE * fit["k"] * 1e-14
    W = -fit["d"]
    nu0 = -fit["d"] / fit["k"]
    txt = (f"$U={fit['k']:.3f}\\,\\nu+({fit['d']:.3f})$\n"
           f"$r={fit['r']:.5f}$\n"
           f"$h={h:.3e}\\ \\mathrm{{J\\cdot s}}$  ({(h/H_TRUE-1)*100:+.1f}%)\n"
           f"$W={W:.3f}\\ \\mathrm{{eV}},\\ \\nu_0={nu0:.3f}\\times10^{{14}}\\mathrm{{Hz}}$")
    ax.text(0.04, 0.96, txt, transform=ax.transAxes, va="top", ha="left", fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#888888", alpha=0.9))
    ax.axvline(nu0, ls=":", color="#999999", lw=1.0)
    ax.set_xlabel("频率 $\\nu$ / $10^{14}\\,\\mathrm{Hz}$")
    ax.set_ylabel(title.split("~")[0].strip() + " / V")
    ax.set_title(title)
    ax.grid(alpha=0.3, ls="--")
    ax.legend(loc="lower right", fontsize=9)
    ax.set_ylim(min(y) - 0.25, max(y) + 0.30)


fig, ax = plt.subplots(figsize=(7.2, 5.4))
draw(ax, NU, U0, fit0, "遏止电压 $U_0$ ~ 频率 $\\nu$", "#1f77b4", "$U_0$ 实测点")
fig.tight_layout()
fig.savefig("fig1_U0_vs_nu.png", dpi=200)
plt.close(fig)

fig, ax = plt.subplots(figsize=(7.2, 5.4))
draw(ax, NU, UD, fitd, "遏止电压 $U_d$ ~ 频率 $\\nu$", "#d62728", "$U_d$ 实测点")
fig.tight_layout()
fig.savefig("fig2_Ud_vs_nu.png", dpi=200)
plt.close(fig)

# 合并对比图
fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.2))
draw(axes[0], NU, U0, fit0, "遏止电压 $U_0$ ~ 频率 $\\nu$", "#1f77b4", "$U_0$ 实测点")
draw(axes[1], NU, UD, fitd, "遏止电压 $U_d$ ~ 频率 $\\nu$", "#d62728", "$U_d$ 实测点")
fig.tight_layout()
fig.savefig("fig3_U0_Ud_对比.png", dpi=200)
plt.close(fig)

print("\n图片已保存: fig1_U0_vs_nu.png / fig2_Ud_vs_nu.png / fig3_U0_Ud_对比.png")

# 供报告使用的数值表
out = {
    "lam": LAM.tolist(), "lam_c": np.round(LAM_C, 1).tolist(),
    "nu": np.round(NU, 3).tolist(), "U0": U0.tolist(), "Id": ID.tolist(),
    "Ud": UD.tolist(),
    "fit0": {k: (float(v) if not isinstance(v, int) else v) for k, v in R0.items()},
    "fitd": {k: (float(v) if not isinstance(v, int) else v) for k, v in Rd.items()},
    "h_avg": float(h_avg), "W_avg": float(W_avg), "nu0_avg": float(n0_avg),
}
with open("_results.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
