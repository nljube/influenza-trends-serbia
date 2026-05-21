# Project Documentation

This directory contains supporting notes for the `influenza-trends-serbia` project, including methodology details, data provenance, and publication or portfolio materials.

## Workflow

1. Collect Google Trends data for predefined influenza-related and control search terms in Serbia.
2. Merge weekly Google Trends data with influenza surveillance data by ISO year and ISO week.
3. Analyze search trends, correlations, and lagged relationships.
4. Generate figures in `outputs/figures/` and summary reports in `outputs/reports/`.
5. Interpret findings as exploratory digital epidemiology signals, not as confirmed influenza incidence.

## Reproducibility

The main workflow is implemented in `src/` and should be run from the repository root. Generated outputs should be reviewed before public use, especially when merged with surveillance data that may require permission or institutional review.
