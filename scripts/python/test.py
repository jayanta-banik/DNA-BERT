import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display as ipydisplay
from scipy.stats import gaussian_kde

# =========================================================
# Based on actual return segments
# =========================================================

segment_df = df_final[df_final["ACTUAL_RETURN"] > 0].copy()

numeric_columns = ["RPA", "ACTUAL_RETURN", "PREDICTED_RETURN"]

for column in numeric_columns:
    segment_df[column] = pd.to_numeric(segment_df[column], errors="coerce")

segment_df = segment_df.replace([np.inf, -np.inf], np.nan)

segment_df = segment_df.dropna(subset=["RPA", "ACTUAL_RETURN", "PREDICTED_RETURN"]).copy()


# =========================================================
# Segment based on ACTUAL_RETURN
# =========================================================

actual_q1 = segment_df["ACTUAL_RETURN"].quantile(0.25)
actual_q3 = segment_df["ACTUAL_RETURN"].quantile(0.75)

segment_df["ACTUAL_RETURN_SEGMENT"] = np.select(
    [segment_df["ACTUAL_RETURN"] > actual_q3, segment_df["ACTUAL_RETURN"].between(actual_q1, actual_q3, inclusive="both"), segment_df["ACTUAL_RETURN"] < actual_q1],
    ["high", "medium", "low"],
    default="unknown",
)

segment_order = ["high", "medium", "low"]

segment_df["ACTUAL_RETURN_SEGMENT"] = pd.Categorical(segment_df["ACTUAL_RETURN_SEGMENT"], categories=segment_order, ordered=True)

segment_df = segment_df.dropna(subset=["ACTUAL_RETURN_SEGMENT"])

print(f"Actual return Q1: {actual_q1:,.4f}")
print(f"Actual return Q3: {actual_q3:,.4f}")


# =========================================================
# 1. RPA histogram for each actual-return segment
# =========================================================

for segment in segment_order:
    segment_values = segment_df.loc[segment_df["ACTUAL_RETURN_SEGMENT"].eq(segment), "RPA"].dropna()

    if segment_values.empty:
        continue

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.hist(segment_values, bins=30, edgecolor="black", alpha=0.75)

    ax.set_title(f"RPA Distribution: {segment.title()} Actual-Return Segment")

    ax.set_xlabel("RPA")
    ax.set_ylabel("Row Count")

    ax.axvline(segment_values.mean(), linestyle="--", label=f"Mean: {segment_values.mean():.3f}")

    ax.axvline(segment_values.median(), linestyle=":", label=f"Median: {segment_values.median():.3f}")

    ax.grid(visible=True, alpha=0.25)

    ax.legend()
    fig.tight_layout()

    ipydisplay(fig)
    plt.close(fig)


# =========================================================
# 2. Total RPA for each actual-return segment
#
# Total RPA =
# 1 - abs(total actual - total predicted) / total actual
# =========================================================

segment_rpa_summary = (
    segment_df.groupby("ACTUAL_RETURN_SEGMENT", observed=True)
    .agg(
        ROW_COUNT=("RPA", "size"),
        MIN_ACTUAL_RETURN=("ACTUAL_RETURN", "min"),
        MAX_ACTUAL_RETURN=("ACTUAL_RETURN", "max"),
        TOTAL_ACTUAL_RETURN=("ACTUAL_RETURN", "sum"),
        TOTAL_PREDICTED_RETURN=("PREDICTED_RETURN", "sum"),
        AVERAGE_ROW_RPA=("RPA", "mean"),
        MEDIAN_ROW_RPA=("RPA", "median"),
    )
    .reset_index()
)

segment_rpa_summary["TOTAL_ABSOLUTE_ERROR"] = segment_rpa_summary["TOTAL_ACTUAL_RETURN"].sub(segment_rpa_summary["TOTAL_PREDICTED_RETURN"]).abs()

segment_rpa_summary["TOTAL_RPA"] = np.where(segment_rpa_summary["TOTAL_ACTUAL_RETURN"] != 0, 1 - (segment_rpa_summary["TOTAL_ABSOLUTE_ERROR"] / segment_rpa_summary["TOTAL_ACTUAL_RETURN"]), np.nan)

segment_rpa_summary["ACTUAL_VOLUME_PERCENT"] = segment_rpa_summary["TOTAL_ACTUAL_RETURN"] / segment_rpa_summary["TOTAL_ACTUAL_RETURN"].sum() * 100

segment_rpa_summary = segment_rpa_summary.sort_values("ACTUAL_RETURN_SEGMENT").reset_index(drop=True)

print("Actual-return segment RPA summary")
display(segment_rpa_summary)


# =========================================================
# Total RPA bar chart
# =========================================================

fig, ax = plt.subplots(figsize=(8, 5))

plot_summary = segment_rpa_summary.dropna(subset=["TOTAL_RPA"])

bars = ax.bar(plot_summary["ACTUAL_RETURN_SEGMENT"].astype(str), plot_summary["TOTAL_RPA"])

ax.set_title("Aggregated RPA by Actual-Return Segment")

ax.set_xlabel("Actual Return Segment")
ax.set_ylabel("Total RPA")

ax.axhline(0.80, linestyle="--", alpha=0.6, label="80% threshold")

ax.axhline(0.60, linestyle=":", alpha=0.6, label="60% threshold")

for bar, value in zip(bars, plot_summary["TOTAL_RPA"]):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.1%}", ha="center", va="bottom")

ax.grid(visible=True, axis="y", alpha=0.25)

ax.legend()
fig.tight_layout()

ipydisplay(fig)
plt.close(fig)


# =========================================================
# 3. Side-by-side actual versus predicted distributions
#
# Fixed bin width = 3
# X-axis labels show only the upper endpoint
# KDE curves are scaled to histogram row counts
# =========================================================

BIN_WIDTH = 3

# Softer shared color, with style differences for comparison
BAR_COLOR = "#7F9DB9"
KDE_COLOR = "#526D82"

for segment in segment_order:
    segment_data = segment_df.loc[segment_df["ACTUAL_RETURN_SEGMENT"].eq(segment)].copy()

    if segment_data.empty:
        continue

    actual_values = segment_data["ACTUAL_RETURN"].dropna().astype(float)

    predicted_values = segment_data["PREDICTED_RETURN"].dropna().astype(float)

    combined_values = pd.concat([actual_values, predicted_values], ignore_index=True)

    if combined_values.empty:
        continue

    # -----------------------------------------------------
    # Create equal-width bins of exactly 3
    # -----------------------------------------------------

    minimum_value = np.floor(combined_values.min() / BIN_WIDTH) * BIN_WIDTH

    maximum_value = np.ceil(combined_values.max() / BIN_WIDTH) * BIN_WIDTH

    # Ensure at least one complete bin exists
    if maximum_value <= minimum_value:
        maximum_value = minimum_value + BIN_WIDTH

    bins = np.arange(minimum_value, maximum_value + BIN_WIDTH, BIN_WIDTH)

    actual_counts, _ = np.histogram(actual_values, bins=bins)

    predicted_counts, _ = np.histogram(predicted_values, bins=bins)

    bin_centers = (bins[:-1] + bins[1:]) / 2

    # Show only the upper endpoint of each bin
    upper_end_labels = [f"{upper_end:g}" for upper_end in bins[1:]]

    x_positions = np.arange(len(bin_centers))

    bar_width = 0.40

    fig, ax = plt.subplots(figsize=(14, 6))

    # -----------------------------------------------------
    # Side-by-side bars
    # -----------------------------------------------------

    actual_bars = ax.bar(x_positions - bar_width / 2, actual_counts, width=bar_width, label="Actual Return", color=BAR_COLOR, alpha=0.72, edgecolor="black", linewidth=0.5)

    predicted_bars = ax.bar(x_positions + bar_width / 2, predicted_counts, width=bar_width, label="Predicted Return", color=BAR_COLOR, alpha=0.42, edgecolor="black", linewidth=0.5, hatch="//")

    # -----------------------------------------------------
    # Count labels above bars
    # -----------------------------------------------------

    ax.bar_label(actual_bars, labels=[f"{count:,}" if count > 0 else "" for count in actual_counts], padding=3, fontsize=8)

    ax.bar_label(predicted_bars, labels=[f"{count:,}" if count > 0 else "" for count in predicted_counts], padding=3, fontsize=8)

    # -----------------------------------------------------
    # KDE curves in the background
    #
    # KDE density is converted to expected bin count:
    # density × row count × bin width
    # -----------------------------------------------------

    kde_x = np.linspace(bins[0], bins[-1], 500)

    def value_to_plot_position(values):
        return (values - bins[0]) / BIN_WIDTH - 0.5

    if len(actual_values) > 1 and actual_values.nunique() > 1:
        actual_kde = gaussian_kde(actual_values)

        actual_kde_counts = actual_kde(kde_x) * len(actual_values) * BIN_WIDTH

        ax.plot(value_to_plot_position(kde_x), actual_kde_counts, color=KDE_COLOR, linewidth=2, alpha=0.55, label="Actual KDE", zorder=1)

    if len(predicted_values) > 1 and predicted_values.nunique() > 1:
        predicted_kde = gaussian_kde(predicted_values)

        predicted_kde_counts = predicted_kde(kde_x) * len(predicted_values) * BIN_WIDTH

        ax.plot(value_to_plot_position(kde_x), predicted_kde_counts, color=KDE_COLOR, linewidth=2, linestyle="--", alpha=0.45, label="Predicted KDE", zorder=1)

    # -----------------------------------------------------
    # Axis formatting
    # -----------------------------------------------------

    ax.set_title(f"Actual vs Predicted Return Distribution: {segment.title()} Actual-Return Segment")

    ax.set_xlabel(f"Return Volume Bin Upper Endpoint (Bin Width = {BIN_WIDTH})")

    ax.set_ylabel("Row Count")

    # Reduce label crowding while keeping upper endpoints
    number_of_bins = len(upper_end_labels)

    if number_of_bins <= 20:
        tick_step = 1
    elif number_of_bins <= 40:
        tick_step = 2
    elif number_of_bins <= 80:
        tick_step = 4
    else:
        tick_step = max(1, int(np.ceil(number_of_bins / 20)))

    visible_tick_positions = x_positions[::tick_step]
    visible_tick_labels = upper_end_labels[::tick_step]

    ax.set_xticks(visible_tick_positions)

    ax.set_xticklabels(visible_tick_labels, rotation=45, ha="right")

    ax.grid(visible=True, axis="y", alpha=0.20)

    ax.legend()

    # Add enough space for labels and KDE
    maximum_bar_count = max(actual_counts.max(initial=0), predicted_counts.max(initial=0))

    kde_maximum = 0

    if len(actual_values) > 1 and actual_values.nunique() > 1:
        kde_maximum = max(kde_maximum, actual_kde_counts.max())

    if len(predicted_values) > 1 and predicted_values.nunique() > 1:
        kde_maximum = max(kde_maximum, predicted_kde_counts.max())

    maximum_height = max(maximum_bar_count, kde_maximum)

    if maximum_height > 0:
        ax.set_ylim(0, maximum_height * 1.20)

    fig.tight_layout()

    ipydisplay(fig)
    plt.close(fig)
