# cupidthatbtc

data analysis and music — mostly Bayesian models for how things get rated.

A lot of rating problems look the same underneath: something collects reviews
over time, each review is a bounded score sitting on a noisy count, and you want
to call the next one. Album scores, pilot ratings, vote shares. panelcast is me
trying to write that model once instead of rebuilding it for every new dataset.

[![now playing](https://bjorkslefteyelash.com/api/nowplaying.svg)](https://stats.fm/cupidthatbtc)

### what's here

- **[panelcast](https://github.com/cupidthatbtc/panelcast)** — hierarchical
  Bayesian forecasting for bounded panel scores. point it at a new dataset with a
  YAML file, no code changes. built on NumPyro / JAX.
- **[aoty_pred_pub](https://github.com/cupidthatbtc/aoty_pred_pub)** — where
  panelcast started: predicting Album of the Year scores. the data plumbing,
  diagnostics, and write-up live here.
- **[bjorkslefteyelash](https://github.com/cupidthatbtc/bjorkslefteyelash)** — a
  self-hosted Björk fan page with a GIF maker bolted on, running on Cloudflare
  Workers.

### tools

Python, NumPyro, JAX, and pandas for the modelling; JavaScript and Cloudflare
Workers for the web side. I spend more time than is reasonable on reproducible
runs and keeping test data out of training.

### the year, scored

<img width="820" src="https://raw.githubusercontent.com/cupidthatbtc/cupidthatbtc/output/github-stats-dark.svg" alt="cupidthatbtc GitHub scorecard — github-readme-stats rank B+ (top 49%), 1,510 commits, 149 pull requests, 79 issues, 30-day best streak; top languages Python and JavaScript" />

<img width="820" src="https://raw.githubusercontent.com/cupidthatbtc/cupidthatbtc/output/github-snake-dark.svg" alt="contribution graph eaten by a snake" />

### lately

<img width="820" src="https://raw.githubusercontent.com/cupidthatbtc/cupidthatbtc/output/listening-dark.svg" alt="stats.fm listening card — top artists over the last 4 weeks: slayr, Brandy, Kanye West, Kim Petras, Madonna" />
