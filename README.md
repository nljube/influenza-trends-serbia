# Influenza Trends Serbia (2013-2025)

Automated Google Trends data extraction and analysis for influenza-related keywords in Serbia, designed for digital epidemiology, infodemiology, and public health surveillance research.

**Author:** Nenad Ljubenovic, MD
**Affiliation:** Department of Epidemiology, Military Medical Academy, Belgrade, Serbia  
**Contact:** nenad@ljubenovic.com  
**License:** MIT

## Project Overview

This repository contains a reproducible Python workflow for collecting, processing, merging, and analyzing Google Trends signals related to influenza in Serbia from 2013 to 2025. The project focuses on weekly search activity for influenza-related symptoms, treatment terms, prevention terms, and negative controls, with optional comparison against influenza surveillance data.

The repository is organized as a portfolio-ready research project. Source code is separated from notebooks, raw data, processed data, and generated outputs.

## Objectives

- Extract weekly Google Trends data for influenza-related Serbian search terms.
- Use overlapping multi-year Google Trends windows to support longer time series collection.
- Merge Google Trends signals with weekly influenza surveillance data.
- Evaluate correlations and lagged relationships between search activity and influenza indicators.
- Generate summary tables and exploratory figures for public health interpretation.

## Methodology

The main extraction script queries Google Trends for predefined Serbian influenza-related keywords using `pytrends`. Because Google Trends normalizes results within each request window, the workflow uses overlapping time windows and rescales adjacent windows based on overlap periods. Weekly trend values are then aggregated by ISO year and ISO week.

Downstream scripts merge the Google Trends data with influenza surveillance data, compute descriptive statistics, Pearson correlations, lagged correlations, and produce exploratory plots. Negative control keywords are included to help contextualize whether associations are disease-specific or reflect broader search behavior.

## Repository Structure

```text
influenza-trends-serbia/
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE
├── src/
│   ├── influenza_gt.py
│   ├── merge_trends_data.py
│   ├── analyze_influenza_trends.py
│   ├── summarize_influenza_trends.py
│   ├── operational_influenza_monitoring.py
│   └── experimental/
├── notebooks/
│   └── models.ipynb
├── data/
│   ├── raw/
│   └── processed/
├── outputs/
│   ├── figures/
│   └── reports/
└── docs/
```

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

## Limitations

- Google Trends values are relative, normalized search interest scores and are not direct measures of disease incidence.
- Google Trends sampling and normalization can vary between repeated requests.
- Internet search behavior is influenced by media attention, healthcare access, seasonality, and population-level behavioral changes.
- Correlation and lag analyses are exploratory and do not establish causality.
- Public release of surveillance data or merged datasets may require institutional review or data owner approval.

## Future Improvements

- Add automated tests for data loading, ISO week conversion, and lag correlation functions.
- Add configuration files for keyword lists, time ranges, and output paths.
- Add reproducible notebook execution with documented environment metadata.
- Compare Google Trends signals with additional respiratory surveillance indicators.
- Add model validation strategies appropriate for time-series data.

## License

This project is released under the MIT License. See `LICENSE` for details.
