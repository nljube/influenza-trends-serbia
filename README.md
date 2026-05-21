# Influenza Trends Serbia

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Jupyter Notebook](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Portfolio%20Project-blue)

Automated Google Trends data extraction and analysis for influenza-related search interest in Serbia. The project is designed as a reproducible digital epidemiology and data science workflow for exploring influenza-related public interest and its potential role as a complementary surveillance signal.

## Author

**Author:** Nenad Ljubenovic, MD  
**Affiliation:** Department of Epidemiology, Military Medical Academy, Belgrade, Serbia  
**Contact:** nenad@ljubenovic.com  
**License:** MIT

## Key Message

This project demonstrates how Google Trends data can be used as a complementary digital epidemiology signal for influenza-related public interest and potential surveillance support in Serbia.

## Project Overview

This repository contains a Python workflow for collecting, processing, merging, and analyzing Google Trends signals related to influenza in Serbia from 2013 to 2025. The analysis focuses on weekly search activity for influenza-related symptoms, treatment terms, prevention terms, and negative controls, with optional comparison against influenza surveillance data.

The repository is structured as a public portfolio project with source code, notebooks, raw and processed data, generated outputs, and documentation separated into dedicated folders.

## Objectives

- Extract weekly Google Trends data for influenza-related Serbian search terms.
- Use overlapping multi-year Google Trends windows to support longer time-series collection.
- Merge Google Trends signals with weekly influenza surveillance data when available.
- Evaluate descriptive patterns, correlations, and lagged relationships.
- Generate summary tables and exploratory figures for public health interpretation.

## Methodology

The main extraction script queries Google Trends for predefined Serbian influenza-related keywords using `pytrends`. Because Google Trends normalizes results within each request window, the workflow uses overlapping time windows and rescales adjacent windows based on overlap periods. Weekly trend values are then aggregated by ISO year and ISO week.

Downstream scripts merge Google Trends data with influenza surveillance data, compute descriptive statistics, Pearson correlations, lagged correlations, and produce exploratory plots. Negative control keywords are included to help contextualize whether observed associations are disease-specific or reflect broader search behavior.

## Repository Structure

```text
influenza-trends-serbia/
├── README.md
├── requirements.txt
├── LICENSE
├── src/
├── notebooks/
├── data/
├── outputs/
└── docs/
```

## Main Scripts

- `src/influenza_gt.py` collects weekly Google Trends data for predefined influenza-related and control keywords in Serbia, using overlapping time windows and overlap-based rescaling.
- `src/merge_trends_data.py` merges weekly Google Trends data with influenza surveillance data by ISO year and ISO week, producing long and wide analytical datasets.
- `src/analyze_influenza_trends.py` computes exploratory correlations and generates figures comparing Google Trends signals with influenza indicators.
- `src/summarize_influenza_trends.py` creates descriptive keyword summaries, keyword-level correlations, and lagged correlation reports.
- `src/operational_influenza_monitoring.py` explores operational monitoring signals using selected influenza-related keywords and lag analysis.

## Notebook

- [notebooks/models.ipynb](notebooks/models.ipynb)

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run commands from the repository root.

Collect Google Trends data:

```bash
python src/influenza_gt.py
```

Merge Google Trends data with influenza surveillance data:

```bash
python src/merge_trends_data.py
```

Generate exploratory correlations and figures:

```bash
python src/analyze_influenza_trends.py --no-show
```

Create summary tables and lagged correlation outputs:

```bash
python src/summarize_influenza_trends.py
```

Run operational lag monitoring:

```bash
python src/operational_influenza_monitoring.py
```

## Outputs

Typical generated outputs include:

- `data/processed/google_trends_weekly_serbia_2013_2025.csv`
- `data/processed/merged_trends_influenza_long.csv`
- `data/processed/merged_trends_influenza_wide.csv`
- `outputs/reports/keyword_summary.csv`
- `outputs/reports/keyword_correlations.csv`
- `outputs/reports/lagged_correlations.csv`
- `outputs/figures/*.png`

Generated files should be reviewed before publication, especially if they contain surveillance data or derived results that require permission to share.

## Example Figures

The following example figures are generated outputs already present in `outputs/figures/`:

![Correlation overview](outputs/figures/correlations.png)

![Google Trends time series for grip](outputs/figures/time_series_grip.png)

![Seasonal profile for grip](outputs/figures/seasonality_grip.png)

## Limitations

- Google Trends reflects search behavior, not confirmed influenza cases.
- Search volume may be influenced by media coverage, public awareness, and changes in internet use.
- Google Trends values are normalized and should be interpreted carefully.
- Official surveillance data are needed for validation.

## Future Work

- Compare trends with official influenza surveillance data.
- Explore lagged correlations.
- Add forecasting models.
- Build a small dashboard.
- Expand analysis to other respiratory infections.

## Portfolio Relevance

This project demonstrates practical skills in:

- Python programming
- Automated data collection
- Data cleaning and aggregation
- Time-series analysis
- Digital epidemiology
- Reproducible public health analytics

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.
