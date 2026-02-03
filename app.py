import streamlit as st
import pandas as pd
from ortools.linear_solver import pywraplp
from collections import Counter
from io import StringIO

st.set_page_config(page_title="昆布組み合わせ最適化", page_icon="🥬")

st.title("🥬 昆布組み合わせ最適化")
st.write("昆布を6枚ずつ袋詰めする最適な組み合わせを計算します")

# サイドバー: 設定
st.sidebar.header("設定")
target_min = st.sidebar.number_input("目標重量（最小）g", value=40.0, step=0.1)
target_max = st.sidebar.number_input("目標重量（最大）g", value=43.0, step=0.1)
pieces_per_bag = st.sidebar.number_input("1袋あたりの枚数", value=6, min_value=1, max_value=20)

# CSVアップロード
st.subheader("1. 在庫データをアップロード")
st.write("CSVファイルに `weights`（重量）と `stock`（在庫数）の列が必要です")

# サンプルCSVダウンロード
sample_csv = """weights,stock
6,20
6.1,3
6.2,6
6.3,5
6.4,9
6.5,9
6.6,10
6.7,10
6.8,13
6.9,10
7,6
7.1,6
7.2,20
7.3,13
7.4,9
7.5,11
7.6,8
7.7,15
7.8,16
7.9,26"""

st.download_button(
    label="📥 サンプルCSVをダウンロード",
    data=sample_csv,
    file_name="kombu_sample.csv",
    mime="text/csv"
)

uploaded_file = st.file_uploader("CSVファイルを選択", type=["csv"])

if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file)

        # 列チェック
        required_cols = {"weights", "stock"}
        missing = required_cols - set(data.columns)
        if missing:
            st.error(f"必要な列がありません: {sorted(missing)}")
            st.stop()

        st.subheader("2. アップロードされた在庫データ")
        st.dataframe(data, use_container_width=True)

        total_pieces = data["stock"].sum()
        st.info(f"合計在庫: {total_pieces}枚")

        # 計算ボタン
        if st.button("🔄 最適化を実行", type="primary"):
            with st.spinner("計算中..."):
                weights = data["weights"].tolist()
                stock = data["stock"].astype(int).tolist()

                # 0.1g単位を整数化
                w_int = [int(round(w * 10)) for w in weights]
                min_sum = int(round(target_min * 10))
                max_sum = int(round(target_max * 10))
                n = len(w_int)

                # 有効パターン生成
                patterns = []
                counts = [0] * n

                def gen_patterns(start_idx, picks_left, sum_so_far):
                    if picks_left == 0:
                        if min_sum <= sum_so_far <= max_sum:
                            patterns.append(counts.copy())
                        return

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

                        if sum_so_far + w + (picks_left - 1) * w > max_sum:
                            break
                        if sum_so_far + w + (picks_left - 1) * max_w < min_sum:
                            continue

                        counts[idx] += 1
                        gen_patterns(idx, picks_left - 1, sum_so_far + w)
                        counts[idx] -= 1

                first_idx = next((i for i, s in enumerate(stock) if s > 0), None)
                if first_idx is None:
                    st.error("在庫がすべて0です")
                    st.stop()

                gen_patterns(first_idx, pieces_per_bag, 0)

                if len(patterns) == 0:
                    st.warning("条件を満たす組み合わせが見つかりませんでした")
                    st.stop()

                # 線形計画
                solver = pywraplp.Solver.CreateSolver("CBC")
                if not solver:
                    st.error("ソルバーの初期化に失敗しました")
                    st.stop()

                x = [solver.IntVar(0, solver.infinity(), f"x_{i}") for i in range(len(patterns))]

                for j in range(n):
                    solver.Add(sum(x[i] * patterns[i][j] for i in range(len(patterns))) <= stock[j])

                solver.Maximize(solver.Sum(x))
                status = solver.Solve()

                if status != pywraplp.Solver.OPTIMAL:
                    st.error("最適解が見つかりませんでした")
                    st.stop()

                # 結果集計
                rows = []
                total_bags = 0
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
                        "組み合わせ": str(combo_weights),
                        "袋数": bags,
                        "合計重量(g)": round(total, 1),
                    })
                    total_bags += bags

                result_df = pd.DataFrame(rows).sort_values(["袋数", "合計重量(g)"], ascending=[False, False])

            # 結果表示
            st.subheader("3. 最適化結果")
            st.success(f"🎉 合計 **{total_bags}袋** 作成可能！")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("作成可能な袋数", f"{total_bags}袋")
            with col2:
                st.metric("使用する昆布", f"{sum(used)}枚")

            st.dataframe(result_df, use_container_width=True)

            # 結果CSVダウンロード
            result_csv = result_df.to_csv(index=False)
            st.download_button(
                label="📥 結果CSVをダウンロード",
                data=result_csv,
                file_name="kombu_result.csv",
                mime="text/csv"
            )

            # 残り在庫
            st.subheader("4. 使用後の在庫")
            inv_df = data.copy()
            inv_df["使用数"] = used
            inv_df["残り"] = inv_df["stock"] - inv_df["使用数"]
            st.dataframe(inv_df, use_container_width=True)

            # 残り在庫CSVダウンロード
            inv_csv = inv_df.to_csv(index=False)
            st.download_button(
                label="📥 残り在庫CSVをダウンロード",
                data=inv_csv,
                file_name="kombu_inventory_after.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# フッター
st.divider()
st.caption("昆布組み合わせ最適化ツール | OR-Toolsを使用した線形計画法")
