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

---

<p>
  <img height="165" src="https://github-readme-stats.vercel.app/api?username=cupidthatbtc&show_icons=true&hide_border=true&theme=tokyonight" alt="cupidthatbtc's GitHub stats" />
  <img height="165" src="https://github-readme-stats.vercel.app/api/top-langs/?username=cupidthatbtc&layout=compact&hide_border=true&theme=tokyonight" alt="top languages" />
</p>

<img src="https://raw.githubusercontent.com/cupidthatbtc/cupidthatbtc/output/github-snake-dark.svg" alt="contribution snake" />
