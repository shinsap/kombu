import pandas as pd
from ortools.linear_solver import pywraplp
from collections import Counter
from datetime import datetime

# ===== 設定 =====
TARGET_MIN_G = 40.0
TARGET_MAX_G = 43.0
PIECES_PER_BAG = 6

INPUT_CSV = "kombu.csv"
SOLVER_NAME = "CBC"  # 環境依存が少ない

# ===== 実行日時（ファイル名用）=====
run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

OUT_COMBINATIONS_CSV = f"optimized_kombu_combinations_{run_ts}.csv"
OUT_INVENTORY_AFTER_CSV = f"kombu_inventory_after_{run_ts}.csv"

# ===== データ読み込み =====
data = pd.read_csv(INPUT_CSV)

required_cols = {"weights", "stock"}
missing = required_cols - set(data.columns)
if missing:
    raise ValueError(f"{INPUT_CSV} に必要な列がありません: {sorted(missing)}")

weights = data["weights"].tolist()
stock = data["stock"].astype(int).tolist()

if len(weights) == 0:
    raise ValueError("weights が空です。")
if len(weights) != len(stock):
    raise ValueError("weights と stock の行数が一致しません。")

# 0.1g単位を整数化（g*10）
w_int = [int(round(w * 10)) for w in weights]
min_sum = int(round(TARGET_MIN_G * 10))
max_sum = int(round(TARGET_MAX_G * 10))
n = len(w_int)

# ===== 有効パターン生成（重複あり、在庫上限も反映）=====
patterns = []  # patternは counts[n]（weight種類ごとの使用枚数）
counts = [0] * n

def gen_patterns(start_idx: int, picks_left: int, sum_so_far: int):
    if picks_left == 0:
        if min_sum <= sum_so_far <= max_sum:
            patterns.append(counts.copy())
        return

    # 枝刈り（残り最小/最大で到達不可能なら終了）
    min_w = w_int[start_idx]
    max_w = w_int[-1]

    if sum_so_far + picks_left * min_w > max_sum:
        return
    if sum_so_far + picks_left * max_w < min_sum:
        return

    for idx in range(start_idx, n):
        if stock[idx] <= 0:
            continue
        if counts[idx] >= stock[idx]:
            continue

        w = w_int[idx]

        # 次以降も idx 以上（非減少）なので、残りの最小は w、最大は max_w
        if sum_so_far + w + (picks_left - 1) * w > max_sum:
            break  # idxが増えるとwも増えるので以降も不可能
        if sum_so_far + w + (picks_left - 1) * max_w < min_sum:
            continue

        counts[idx] += 1
        gen_patterns(idx, picks_left - 1, sum_so_far + w)
        counts[idx] -= 1

# 探索開始位置（最初に在庫があるweight）
first_idx = next((i for i, s in enumerate(stock) if s > 0), None)
if first_idx is None:
    raise ValueError("在庫がすべて0です。")

gen_patterns(first_idx, PIECES_PER_BAG, 0)

print("有効パターン数:", len(patterns))

# ===== デバッグ出力（生成された合計重量の分布）=====
pattern_totals = [sum(c * w for c, w in zip(cnts, w_int)) for cnts in patterns]
c = Counter(pattern_totals)
print("生成された合計重量:", sorted({t / 10 for t in c.keys()}))
print("42.0〜42.9 のパターン数:", sum(v for k, v in c.items() if 420 <= k <= 429))
print("43.0 のパターン数:", c.get(430, 0))

# ===== 線形計画（袋数最大化）=====
solver = pywraplp.Solver.CreateSolver(SOLVER_NAME)
if not solver:
    raise RuntimeError(f"Solver could not be created ({SOLVER_NAME}).")

x = [solver.IntVar(0, solver.infinity(), f"x_{i}") for i in range(len(patterns))]

# 在庫制約：sum_i x_i * pattern_i[j] <= stock[j]
for j in range(n):
    solver.Add(sum(x[i] * patterns[i][j] for i in range(len(patterns))) <= stock[j])

solver.Maximize(solver.Sum(x))
status = solver.Solve()

if status != pywraplp.Solver.OPTIMAL:
    print("Solver did not find an optimal solution.")
    raise SystemExit(1)

# ===== 結果出力（組み合わせ + 合計袋数行）=====
rows = []
total_bags = 0

# weightごとの使用枚数集計
used = [0] * n

for i, cnts in enumerate(patterns):
    bags = int(round(x[i].solution_value()))
    if bags <= 0:
        continue

    combo_weights = []
    for j, c_j in enumerate(cnts):
        if c_j:
            combo_weights.extend([weights[j]] * c_j)
            used[j] += bags * c_j

    total = sum(combo_weights)
    rows.append({
        "Combination (Weights)": combo_weights,
        "Bags": bags,
        "Total Weight (g)": total,
    })
    total_bags += bags

out_df = pd.DataFrame(rows).sort_values(["Bags", "Total Weight (g)"], ascending=[False, False])

# 最終行に合計袋数
total_row = pd.DataFrame([{
    "Combination (Weights)": "TOTAL",
    "Bags": total_bags,
    "Total Weight (g)": ""
}])

out_df_with_total = pd.concat([out_df, total_row], ignore_index=True)
out_df_with_total.to_csv(OUT_COMBINATIONS_CSV, index=False)
print(f"結果を '{OUT_COMBINATIONS_CSV}' に保存しました。")
print("合計袋数:", total_bags)

# ===== 最新在庫CSVの自動生成（使用数差し引き）=====
inv_df = data.copy()
inv_df["used"] = used
inv_df["remaining"] = inv_df["stock"] - inv_df["used"]

# 念のためマイナス検知（本来は発生しない想定）
if (inv_df["remaining"] < 0).any():
    neg = inv_df[inv_df["remaining"] < 0][["weights", "stock", "used", "remaining"]]
    print("WARNING: remaining がマイナスの行があります（在庫制約の想定外）")
    print(neg.to_string(index=False))

inv_df.to_csv(OUT_INVENTORY_AFTER_CSV, index=False)
print(f"最新在庫を '{OUT_INVENTORY_AFTER_CSV}' に保存しました。")
