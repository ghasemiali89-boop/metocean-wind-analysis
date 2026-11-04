# Wind Direction & Daily Maximum Wind Speed Analysis

A reusable Python/Jupyter workflow for **daily maximum wind speed and its corresponding direction**.
It loads Excel data, converts wide monthly tables to tidy daily records, checks basic data quality, calculates descriptive statistics and exports figures and Excel/CSV tables.

## راهنمای سریع (فارسی)

**۱.** کد را دریافت کنید و پوشه پروژه را باز کنید.

**۲.** فایل ورودی را در `data/` قرار دهید؛ مثلاً با نام `wind_data.xlsx`.
**فایل واقعی داده در مخزن قرار داده نشده است.** پیش از انتشار داده‌های واقعی مجوز انتشار و محرمانگی آنها را بررسی کنید.

**۳.** مسیر فایل را در ابتدای فایل `wind_analysis.py` تغییر دهید:

```python
INPUT_FILE = PROJECT_DIR / "data" / "wind_data.xlsx"
```

یا از آدرس کامل ویندوز استفاده کنید (به `r` قبل از رشته توجه کنید):

```python
INPUT_FILE = Path(r"C:\Users\YOUR_NAME\Desktop\wind\wind speed and direction.xlsx")
```

برای اجرای نوت‌بوک، مسیر در **اولین سلول تنظیمات** قابل تغییر است.

**۴.** نصب کتابخانه‌ها در Terminal یا Anaconda Prompt:

```bash
python -m pip install -r requirements.txt
```

**۵.** اجرای اسکریپت:

```bash
python wind_analysis.py
```

یا:

```bash
jupyter lab
```

و فایل `Wind_Analysis.ipynb` را باز کرده و `Run All` را اجرا کنید.

**۶.** خروجی‌ها در پوشه `outputs/` ساخته می‌شوند: PNG با کیفیت 300 DPI، PDF برداری، CSV مرتب‌شده و یک فایل Excel دارای جدول‌های آمار.

## Input formats

### Option A: Wide Persian-month spreadsheet (default)

- Sheet name: `Sheet1` (editable through `INPUT_SHEET`)
- Row 1: month/year headers, e.g. `فروردین 1389`, `اردیبهشت 1389`, ...
- Row 2: repeated `Dir`, `Wind` columns
- Column A from row 3 onward: day-of-month (`1` through `31`)
- Remaining columns: one paired direction and daily maximum speed per month
- Directions **0° and 360°** both represent North in the default interpretation

The input is automatically converted from wide to long; **no manual Excel rearrangement is necessary**.
The example workbook covers 1389–1404. The `PERSIAN_LEAP_YEARS` set at the top of the script covers this period; **update the set if analyzing other Solar Hijri years**, especially for Esfand 30.

### Option B: Long CSV or Excel

Set `INPUT_LAYOUT = "long"` and provide these columns:

| Year | Month | Day | Direction | WindSpeed |
|---:|---:|---:|---:|---:|
| 1401 | 1 | 1 | 220 | 8.5 |
| 1401 | 1 | 2 | 270 | 12.0 |

`Direction` is in degrees clockwise from North **(direction wind comes from)**. `WindSpeed` is in `m/s` by default.

## User-configurable parameters

| Setting | Purpose |
|---|---|
| `INPUT_FILE` | Path of the source workbook/CSV |
| `INPUT_LAYOUT` | `wide` or `long` |
| `INPUT_SHEET` | Excel sheet name |
| `OUTPUT_DIR` | Output directory |
| `STRONG_WIND_THRESHOLD` | Strong winds are **strictly greater** than this value (default 12 m/s) |
| `DIRECTION_BIN_DEG` | Angular sector width (default 10 degrees) |
| `SPEED_BIN_EDGES` | Wind-speed groups for the wind rose and joint heatmap |
| `PERSIAN_LEAP_YEARS` | Update for different years |

**Note:** The polar wind-rose diagram requires `360 / DIRECTION_BIN_DEG` to be an integer. Use e.g. 10°, 15°, 20° or 30°.

## Output contents

- `Fig_01_WindSpeed_Histogram`: speed histogram
- `Fig_02_WindSpeed_Exceedance`: empirical exceedance frequency (%)
- `Fig_03_WindRose_10deg`: wind rose by speed and direction (Matplotlib polar axes; no separate windrose package needed)
- `Fig_04_Direction_Comparison`: all observations vs high-speed subset
- `Fig_05_Joint_Speed_Direction`: direction × speed frequency heatmap
- `Fig_06_Monthly_Boxplot`: monthly speed distributions
- `Fig_07_Annual_Variation`: annual mean, P95 and annual maximum
- `Wind_Analysis_Tables.xlsx`: statistics, directional frequencies and summary tables
- `WindData_Long.csv`: tidy daily observations

The `outputs/` folder is ignored by Git by default. Add selected figures to a public repository only if you have publication rights.

## Statistical interpretation notes

- The input consists of **daily maxima and their associated directions**, not complete hourly observations. Hence the “dominant direction” is the most common direction *associated with daily maxima*.
- Direction at wind speed 0 is treated as undefined; these zero-speed days remain in the **speed** analysis but are excluded from **directional** plots.
- Missing days are preserved in the daily table. Frequency denominators use valid observations; coverage is reported for monthly and annual analysis.
- The empirical exceedance percentage is **not an extreme-event return period**.
- Significant changes between years may reflect station or measurement-system changes; investigate source homogeneity before claiming a climatic trend.
- This is an engineering **analysis workflow**, not an accredited metocean design standard or design-wind estimator.

## Dependencies

Python 3.10+ recommended. See [`requirements.txt`](requirements.txt).

## Sharing and citation

When publishing, describe the script as a **custom, reproducible analysis workflow built on established Python libraries** rather than claiming that existing software cannot perform these analyses. Check rights to release source observations separately from the code.

## Example outputs / نمونه نمودارهای خروجی

The following illustrations are included as examples generated from the sample observation period. They are **not** substitute input data. If you share these figures publicly, ensure you have the right to publish results derived from the original observations.

**Wind rose / گلباد ۱۰ درجه‌ای**

![10-degree wind rose](examples/Example_01_WindRose_10deg.png)

**Joint speed–direction distribution / توزیع مشترک**

![Joint speed and direction](examples/Example_02_Joint_Distribution.png)

**Empirical exceedance / احتمال فراگذشت**

![Exceedance curve](examples/Example_03_Exceedance.png)

**Annual variation / تغییرات سالانه**

![Annual wind-speed variation](examples/Example_04_Annual_Variation.png)
