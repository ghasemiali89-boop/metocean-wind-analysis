"""Reproducible statistical analysis of daily maximum wind speed and direction.

Inputs:
    (A) wide Excel: 2 header rows, first column Day, monthly Dir/Wind pairs;
    (B) long Excel/CSV: Year, Month, Day, Direction, WindSpeed columns.

Run:
    python wind_analysis.py

Configure INPUT_FILE, INPUT_LAYOUT and OUTPUT_DIR in the USER SETTINGS section.
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ===========================================================================
# USER SETTINGS - EDIT THESE VALUES BEFORE RUNNING
# ===========================================================================
PROJECT_DIR = Path(__file__).resolve().parent

# 1) Where is your input file? Choose ONE option.
# Relative project path (recommended for GitHub; do not publish private data):
INPUT_FILE = PROJECT_DIR / "data" / "wind_data.xlsx"
# Windows absolute path example (remove # and edit if you prefer):
# INPUT_FILE = Path(r"C:\Users\YOUR_NAME\Desktop\wind\wind speed and direction.xlsx")

# 2) Excel sheet (ignored when reading a CSV file):
INPUT_SHEET = "Sheet1"

# 3) 'wide' = monthly paired columns (Dir, Wind) with Persian month/year headers;
#    'long' = Year, Month, Day, Direction, WindSpeed as separate columns.
INPUT_LAYOUT = "wide"

# 4) Destination folder for tables and images:
OUTPUT_DIR = PROJECT_DIR / "outputs"

# 5) Units and analysis controls:
WIND_SPEED_UNIT = "m/s"
STRONG_WIND_THRESHOLD = 12.0  # 'strong' means STRICTLY greater than 12 m/s
DIRECTION_BIN_DEG = 10         # 36 directional sectors, center = 0, 10, ... 350
SPEED_BIN_EDGES = [0, 3, 6, 9, 12, 15, 20]  # last bin is >= 20

# Solar Hijri leap years covered by the example workbook (1389–1404).
# IMPORTANT: Update this set if using other Persian calendar years.
PERSIAN_LEAP_YEARS = {1391, 1395, 1399, 1403}
# ===========================================================================

MONTH_MAP = {
    "فروردین": 1, "اردیبهشت": 2, "خرداد": 3, "تیر": 4,
    "مرداد": 5, "شهریور": 6, "مهر": 7, "آبان": 8,
    "آذر": 9, "دی": 10, "بهمن": 11, "اسفند": 12,
}
DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_header(value: object) -> str:
    """Normalize Persian/Arabic digits and minor typography differences."""
    return (str(value).translate(DIGIT_MAP)
            .replace("ي", "ی").replace("ك", "ک")
            .replace("\u200c", " ").replace("\xa0", " ").strip())


def jalali_days_in_month(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid Persian month: {month}")
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    return 30 if year in PERSIAN_LEAP_YEARS else 29


def read_wide_excel(input_file: Path, sheet_name: str = INPUT_SHEET) -> pd.DataFrame:
    """Convert one 'Day + paired monthly Dir/Wind' workbook to tidy daily records."""
    raw = pd.read_excel(input_file, sheet_name=sheet_name, header=None)
    if raw.shape[0] < 3 or raw.shape[1] < 3 or (raw.shape[1] - 1) % 2:
        raise ValueError(
            f"Unexpected wide sheet dimensions {raw.shape}. "
            "Expected first column Day and then pairs of Direction/Wind."
        )
    day_column = pd.to_numeric(raw.iloc[2:, 0], errors="coerce")
    monthly_frames = []

    for col in range(1, raw.shape[1], 2):
        header = normalize_header(raw.iat[0, col])
        match = re.fullmatch(r"(.+?)\s+(\d{4})", header)
        if not match:
            raise ValueError(f"Month/year header not recognized at column {col+1}: {header!r}")
        month_name, year_text = match.groups()
        month = MONTH_MAP.get(month_name.strip())
        if month is None:
            raise ValueError(f"Unknown Persian month {month_name!r} in {header!r}")
        year = int(year_text)

        first_label = normalize_header(raw.iat[1, col]).casefold()
        second_label = normalize_header(raw.iat[1, col + 1]).casefold()
        if {first_label, second_label} != {"dir", "wind"}:
            raise ValueError(
                f"Expected Dir and Wind in columns {col+1}/{col+2}, "
                f"got {first_label!r}/{second_label!r}"
            )
        dcol = col if first_label == "dir" else col + 1
        scol = col if first_label == "wind" else col + 1

        temp = pd.DataFrame({
            "Year": year,
            "Month": month,
            "Day": day_column.to_numpy(),
            "Direction": raw.iloc[2:, dcol].to_numpy(),
            "WindSpeed": raw.iloc[2:, scol].to_numpy(),
        })
        max_day = jalali_days_in_month(year, month)
        temp = temp.loc[temp["Day"].between(1, max_day)].copy()
        monthly_frames.append(temp)

    if not monthly_frames:
        raise ValueError("No month blocks were found in the wide workbook")
    return pd.concat(monthly_frames, ignore_index=True)


def read_long_table(input_file: Path, sheet_name: str = INPUT_SHEET) -> pd.DataFrame:
    """Read an already tidy Excel/CSV table with standardized column names."""
    if input_file.suffix.lower() == ".csv":
        df = pd.read_csv(input_file)
    else:
        df = pd.read_excel(input_file, sheet_name=sheet_name)
    df = df.rename(columns=lambda c: str(c).strip())
    required = {"Year", "Month", "Day", "Direction", "WindSpeed"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing long-data columns: {sorted(missing)}")
    return df[["Year", "Month", "Day", "Direction", "WindSpeed"]].copy()


def prepare_data(
    input_file: Path = INPUT_FILE,
    input_layout: str = INPUT_LAYOUT,
    sheet_name: str = INPUT_SHEET,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    """Read, normalize and return all calendar records, valid-speed data,
    direction-bearing records and a compact quality summary.
    """
    input_file = Path(input_file).expanduser()
    if not input_file.is_file():
        raise FileNotFoundError(
            f"Cannot find input file: {input_file}\n"
            "Edit INPUT_FILE at the top of wind_analysis.py, or put the Excel file "
            "in the data/ folder as wind_data.xlsx."
        )
    if input_layout == "wide":
        if input_file.suffix.lower() != ".xlsx":
            raise ValueError("INPUT_LAYOUT='wide' currently requires .xlsx")
        df = read_wide_excel(input_file, sheet_name)
    elif input_layout == "long":
        df = read_long_table(input_file, sheet_name)
    else:
        raise ValueError("INPUT_LAYOUT must be 'wide' or 'long'")

    for col in ["Year", "Month", "Day", "Direction", "WindSpeed"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[["Year", "Month", "Day"]].isna().any().any():
        raise ValueError("Some rows have missing/invalid Year, Month or Day")
    df[["Year", "Month", "Day"]] = df[["Year", "Month", "Day"]].astype(int)
    df = df.sort_values(["Year", "Month", "Day"]).reset_index(drop=True)
    if df.duplicated(["Year", "Month", "Day"]).any():
        raise ValueError("Duplicate Year/Month/Day rows found; resolve before analysis")

    invalid_speed = df["WindSpeed"].notna() & (df["WindSpeed"] < 0)
    invalid_direction = df["Direction"].notna() & ~df["Direction"].between(0, 360)
    df.loc[invalid_speed, "WindSpeed"] = np.nan
    df.loc[invalid_direction, "Direction"] = np.nan

    # Speed analysis uses every valid speed. Directional analysis needs both
    # values and positive speed: direction at 0 m/s is physically undefined.
    df_speed = df.dropna(subset=["WindSpeed"]).copy()
    df_dir = df.dropna(subset=["WindSpeed", "Direction"]).copy()
    df_dir = df_dir.loc[df_dir["WindSpeed"] > 0].copy()
    df_dir["Direction_clean"] = df_dir["Direction"] % 360
    df_dir["Sector10"] = (
        ((df_dir["Direction_clean"] + DIRECTION_BIN_DEG / 2) % 360)
        // DIRECTION_BIN_DEG
    ).astype(int) * DIRECTION_BIN_DEG

    summary = pd.Series({
        "Calendar records": len(df),
        "Records with speed": len(df_speed),
        "Records with direction and positive speed": len(df_dir),
        "Missing/invalid speed": int(df["WindSpeed"].isna().sum()),
        "Missing/invalid direction": int(df["Direction"].isna().sum()),
        "Invalid negative speeds found": int(invalid_speed.sum()),
        "Directions outside 0..360 found": int(invalid_direction.sum()),
        "Zero-speed records": int((df_speed["WindSpeed"] == 0).sum()),
        "Coverage (%)": 100 * len(df_speed) / len(df) if len(df) else np.nan,
    })
    return df, df_speed, df_dir, summary


def analyze_wind(
    df: pd.DataFrame, df_speed: pd.DataFrame, df_dir: pd.DataFrame
) -> dict[str, pd.DataFrame | pd.Series]:
    speeds = df_speed["WindSpeed"]
    wind_stats = pd.Series({
        "Count": int(speeds.count()),
        f"Mean ({WIND_SPEED_UNIT})": speeds.mean(),
        f"Median ({WIND_SPEED_UNIT})": speeds.median(),
        f"Std ({WIND_SPEED_UNIT})": speeds.std(),
        "CV (%)": 100 * speeds.std() / speeds.mean() if speeds.mean() else np.nan,
        f"Minimum ({WIND_SPEED_UNIT})": speeds.min(),
        f"Maximum ({WIND_SPEED_UNIT})": speeds.max(),
        f"P90 ({WIND_SPEED_UNIT})": speeds.quantile(.90),
        f"P95 ({WIND_SPEED_UNIT})": speeds.quantile(.95),
        f"P99 ({WIND_SPEED_UNIT})": speeds.quantile(.99),
        "Skewness": speeds.skew(),
    })
    thresholds = np.arange(0, np.ceil(speeds.max()) + .5, .5)
    exceedance = pd.DataFrame({
        "Threshold (m/s)": thresholds,
        "Exceedance (%)": [100 * (speeds > x).mean() for x in thresholds],
    })
    sectors = np.arange(0, 360, DIRECTION_BIN_DEG)
    all_counts = df_dir["Sector10"].value_counts().reindex(sectors, fill_value=0)
    strong_dir = df_dir.loc[df_dir["WindSpeed"] > STRONG_WIND_THRESHOLD]
    strong_counts = strong_dir["Sector10"].value_counts().reindex(sectors, fill_value=0)
    direction = pd.DataFrame({
        "Sector (deg)": sectors,
        "All count": all_counts.to_numpy(),
        "All frequency (%)": 100 * all_counts.to_numpy() / len(df_dir),
        "Strong count": strong_counts.to_numpy(),
        "Strong frequency (%)": (
            100 * strong_counts.to_numpy() / len(strong_dir)
            if len(strong_dir) else np.zeros(len(sectors))
        ),
        "Strong rate within sector (%)": np.divide(
            100 * strong_counts.to_numpy(), all_counts.to_numpy(),
            out=np.zeros(len(sectors), dtype=float), where=all_counts.to_numpy() > 0
        ),
    })
    speed_edges = SPEED_BIN_EDGES + [np.inf]
    speed_labels = [
        f"{SPEED_BIN_EDGES[i]}–<{SPEED_BIN_EDGES[i+1]}"
        for i in range(len(SPEED_BIN_EDGES) - 1)
    ] + [f">={SPEED_BIN_EDGES[-1]}"]
    speed_categories = pd.cut(
        df_dir["WindSpeed"], bins=speed_edges,
        labels=speed_labels, right=False,
    )
    joint_counts = pd.crosstab(speed_categories, df_dir["Sector10"]).reindex(
        index=speed_labels, columns=sectors, fill_value=0
    )
    joint_percent = joint_counts / len(df_dir) * 100

    monthly = df.groupby("Month").agg(
        CalendarDays=("Day", "size"),
        ValidDays=("WindSpeed", "count"),
        MeanSpeed=("WindSpeed", "mean"),
        MedianSpeed=("WindSpeed", "median"),
        P95=("WindSpeed", lambda x: x.quantile(.95)),
        MaximumSpeed=("WindSpeed", "max"),
        StrongDays=("WindSpeed", lambda x: (x > STRONG_WIND_THRESHOLD).sum()),
    )
    monthly["Coverage (%)"] = monthly["ValidDays"] / monthly["CalendarDays"] * 100
    monthly["StrongWind (%)"] = np.where(
        monthly["ValidDays"] > 0,
        monthly["StrongDays"] / monthly["ValidDays"] * 100, np.nan
    )
    annual = df.groupby("Year").agg(
        CalendarDays=("Day", "size"),
        ValidDays=("WindSpeed", "count"),
        MeanSpeed=("WindSpeed", "mean"),
        MedianSpeed=("WindSpeed", "median"),
        P95=("WindSpeed", lambda x: x.quantile(.95)),
        MaximumSpeed=("WindSpeed", "max"),
        StrongDays=("WindSpeed", lambda x: (x > STRONG_WIND_THRESHOLD).sum()),
    )
    annual["Coverage (%)"] = annual["ValidDays"] / annual["CalendarDays"] * 100
    annual["StrongWind (%)"] = np.where(
        annual["ValidDays"] > 0,
        annual["StrongDays"] / annual["ValidDays"] * 100, np.nan
    )
    top10 = df_dir.nlargest(10, "WindSpeed")[[
        "Year", "Month", "Day", "WindSpeed", "Direction_clean", "Sector10"
    ]]
    return {
        "stats": wind_stats, "exceedance": exceedance, "direction": direction,
        "joint_counts": joint_counts, "joint_percent": joint_percent,
        "monthly": monthly, "annual": annual, "top10": top10,
    }


def save_figure(fig: plt.Figure, basename: str, output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{basename}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{basename}.pdf", bbox_inches="tight")
    plt.show()
    plt.close(fig)


def plot_speed_distribution(df_speed: pd.DataFrame, output_dir: Path = OUTPUT_DIR) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.hist(df_speed["WindSpeed"], bins=20, edgecolor="white")
    ax.set(title="Distribution of Daily Maximum Wind Speed",
           xlabel=f"Daily Maximum Wind Speed ({WIND_SPEED_UNIT})", ylabel="Number of Days")
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    save_figure(fig, "Fig_01_WindSpeed_Histogram", output_dir)


def plot_exceedance(results: dict, output_dir: Path = OUTPUT_DIR) -> None:
    exc = results["exceedance"]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(exc["Threshold (m/s)"], exc["Exceedance (%)"], linewidth=2)
    ax.set(title="Empirical Exceedance of Daily Maximum Wind Speed",
           xlabel=f"Threshold ({WIND_SPEED_UNIT})", ylabel="Exceedance Frequency (%)")
    ax.set_ylim(0, 100)
    ax.grid(alpha=.25)
    fig.tight_layout()
    save_figure(fig, "Fig_02_WindSpeed_Exceedance", output_dir)


def plot_windrose(df_dir: pd.DataFrame, annual: pd.DataFrame,
                  output_dir: Path = OUTPUT_DIR) -> None:
    # Draw the wind rose directly using Matplotlib polar axes; no windrose
    # add-on is required. Each bar is a directional sector, stacked by speed.
    nsector = int(360 / DIRECTION_BIN_DEG)
    if nsector * DIRECTION_BIN_DEG != 360:
        raise ValueError("DIRECTION_BIN_DEG must divide 360 exactly")
    sector_index = (
        ((df_dir["Direction_clean"].to_numpy() + DIRECTION_BIN_DEG / 2) % 360)
        // DIRECTION_BIN_DEG
    ).astype(int)
    speed_index = np.searchsorted(
        np.asarray(SPEED_BIN_EDGES, dtype=float),
        df_dir["WindSpeed"].to_numpy(), side="right"
    ) - 1
    classes = len(SPEED_BIN_EDGES)
    counts = np.zeros((nsector, classes), dtype=float)
    np.add.at(counts, (sector_index, speed_index), 1)
    percent = counts / len(df_dir) * 100

    fig, ax = plt.subplots(figsize=(9, 8), subplot_kw={"projection": "polar"})
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)  # clockwise, meteorological "from" direction
    centers = np.deg2rad(np.arange(nsector) * DIRECTION_BIN_DEG)
    width = np.deg2rad(DIRECTION_BIN_DEG * .90)
    bottoms = np.zeros(nsector)
    colors = plt.get_cmap("viridis")(np.linspace(.05, .98, classes))
    speed_labels = [
        f"{SPEED_BIN_EDGES[i]}–<{SPEED_BIN_EDGES[i+1]}"
        for i in range(classes - 1)
    ] + [f">={SPEED_BIN_EDGES[-1]}"]
    for i in range(classes):
        ax.bar(centers, percent[:, i], width=width, bottom=bottoms,
               color=colors[i], edgecolor="white", linewidth=.35,
               align="center", label=speed_labels[i])
        bottoms += percent[:, i]
    ax.set_xticks(np.deg2rad(np.arange(0, 360, 45)))
    ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
    ax.set_rlabel_position(25)
    ax.grid(alpha=.30)
    ax.set_title(
        f"Wind Rose of Daily Maximum Wind Speed\n"
        f"Period: {int(annual.index.min())}–{int(annual.index.max())} (Persian Calendar)",
        fontsize=12, pad=25)
    ax.legend(title=f"Wind Speed ({WIND_SPEED_UNIT})",
              loc="upper left", bbox_to_anchor=(1.12, 1.05))
    save_figure(fig, "Fig_03_WindRose_10deg", output_dir)


def plot_direction_comparison(results: dict, output_dir: Path = OUTPUT_DIR) -> None:
    d = results["direction"]
    x = np.arange(len(d))
    width = .42
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.bar(x - width / 2, d["All frequency (%)"], width, label="All valid directions")
    ax.bar(x + width / 2, d["Strong frequency (%)"], width,
           label=f"Strong winds (> {STRONG_WIND_THRESHOLD:g} {WIND_SPEED_UNIT})")
    ax.set_xticks(x)
    ax.set_xticklabels(d["Sector (deg)"], rotation=90)
    ax.set(title="Wind Direction: All Records vs Strong-Wind Records",
           xlabel="Direction Sector Center (deg)", ylabel="Frequency within each group (%)")
    ax.legend()
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    save_figure(fig, "Fig_04_Direction_Comparison", output_dir)


def plot_joint_distribution(results: dict, output_dir: Path = OUTPUT_DIR) -> None:
    values = results["joint_percent"]
    fig, ax = plt.subplots(figsize=(13, 5.5))
    im = ax.imshow(values.to_numpy(), aspect="auto", origin="lower",
                   interpolation="nearest", cmap="viridis")
    ax.set_xticks(np.arange(0, len(values.columns), 3))
    ax.set_xticklabels(values.columns[::3])
    ax.set_yticks(np.arange(len(values.index)))
    ax.set_yticklabels(values.index)
    ax.set(title="Joint Distribution of Wind Speed and Direction",
           xlabel="Direction Sector Center (deg)",
           ylabel=f"Wind Speed Class ({WIND_SPEED_UNIT})")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Frequency (% of valid directional records)")
    fig.tight_layout()
    save_figure(fig, "Fig_05_Joint_Speed_Direction", output_dir)


def plot_monthly_boxplot(df_speed: pd.DataFrame, output_dir: Path = OUTPUT_DIR) -> None:
    month_data = [df_speed.loc[df_speed["Month"] == month, "WindSpeed"].to_numpy()
                  for month in range(1, 13)]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.boxplot(month_data, positions=list(range(1, 13)), widths=.6)
    ax.set_xticks(range(1, 13))
    ax.set(title="Monthly Distribution of Daily Maximum Wind Speed",
           xlabel="Persian Calendar Month", ylabel=f"Daily Maximum Wind Speed ({WIND_SPEED_UNIT})")
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    save_figure(fig, "Fig_06_Monthly_Boxplot", output_dir)


def plot_annual_variation(results: dict, output_dir: Path = OUTPUT_DIR) -> None:
    annual = results["annual"]
    years = annual.index.to_numpy(dtype=int)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(years, annual["MeanSpeed"], marker="o", label="Annual Mean")
    axes[0].plot(years, annual["P95"], marker="s", label="Annual P95")
    axes[0].set(title="Annual Variation of Daily Maximum Wind Speed",
                ylabel=f"Wind Speed ({WIND_SPEED_UNIT})")
    axes[0].legend()
    axes[1].plot(years, annual["MaximumSpeed"], marker="o", label="Annual Maximum")
    axes[1].set(xlabel="Persian Calendar Year", ylabel=f"Annual Maximum ({WIND_SPEED_UNIT})")
    axes[1].legend()
    for ax in axes:
        ax.grid(alpha=.25)
        for year in annual.loc[annual["Coverage (%)"] < 95].index:
            ax.axvspan(year-.4, year+.4, color="gray", alpha=.12)
    axes[1].set_xticks(years)
    axes[1].tick_params(axis="x", labelrotation=45)
    fig.tight_layout()
    save_figure(fig, "Fig_07_Annual_Variation", output_dir)


def export_results(df: pd.DataFrame, df_speed: pd.DataFrame,
                   df_dir: pd.DataFrame, quality: pd.Series, results: dict,
                   output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "WindData_Long.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(output_dir / "Wind_Analysis_Tables.xlsx", engine="openpyxl") as writer:
        quality.to_frame("Value").to_excel(writer, sheet_name="Data_Quality")
        results["stats"].to_frame("Value").to_excel(writer, sheet_name="Speed_Statistics")
        results["exceedance"].to_excel(writer, sheet_name="Exceedance", index=False)
        results["direction"].to_excel(writer, sheet_name="Direction_10deg", index=False)
        results["joint_counts"].to_excel(writer, sheet_name="Joint_Count")
        results["joint_percent"].to_excel(writer, sheet_name="Joint_Percent")
        results["monthly"].to_excel(writer, sheet_name="Monthly")
        results["annual"].to_excel(writer, sheet_name="Annual")
        results["top10"].to_excel(writer, sheet_name="Top_10", index=False)


def print_summary(quality: pd.Series, results: dict) -> None:
    direction = results["direction"]
    most_common = direction.loc[direction["All count"].idxmax()]
    strong_count = int(direction["Strong count"].sum())
    print("\n=== Wind Analysis Summary ===")
    print(quality.to_string())
    print("\nSpeed statistics:")
    print(results["stats"].round(2).to_string())
    print(f"\nMost frequent {DIRECTION_BIN_DEG}-degree direction sector: "
          f"{most_common['Sector (deg)']:.0f}°; "
          f"{most_common['All frequency (%)']:.2f}%")
    print(f"Strong-wind records (> {STRONG_WIND_THRESHOLD:g} {WIND_SPEED_UNIT}): "
          f"{strong_count}")
    if strong_count:
        row = direction.loc[direction["Strong count"].idxmax()]
        print(f"Most frequent strong-wind sector: {row['Sector (deg)']:.0f}°; "
              f"{row['Strong frequency (%)']:.2f}% of strong-wind records")
    print("\nNOTE: Observations are daily maxima, not an hourly wind climatology.")
    print("NOTE: Missing days and possible station/instrument changes need review ")
    print("      before climatological trend or extreme-value interpretation.")


def run_analysis(
    input_file: Path = INPUT_FILE,
    input_layout: str = INPUT_LAYOUT,
    output_dir: Path = OUTPUT_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    df, df_speed, df_dir, quality = prepare_data(input_file, input_layout)
    results = analyze_wind(df, df_speed, df_dir)
    export_results(df, df_speed, df_dir, quality, results, output_dir)
    plot_speed_distribution(df_speed, output_dir)
    plot_exceedance(results, output_dir)
    plot_windrose(df_dir, results["annual"], output_dir)
    plot_direction_comparison(results, output_dir)
    plot_joint_distribution(results, output_dir)
    plot_monthly_boxplot(df_speed, output_dir)
    plot_annual_variation(results, output_dir)
    print_summary(quality, results)
    print(f"\nOutputs saved in: {output_dir.resolve()}")
    return df, df_speed, df_dir, results


if __name__ == "__main__":
    run_analysis()
