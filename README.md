# SupeRR Selector Season 2 — Most Reliable Players Under Pressure

A data-driven system that scores every IPL and T20I delivery (2022–2026) for **batting pressure** and
**bowling pressure**, measures each player against an average player in the same situation and against his own
usual level, and ranks the players who deliver most consistently when it matters. It includes
**SUPERR INTELLIGENCE**, a 10-page Streamlit dashboard.

**Selection rules** (in `config/settings.py`): only players who played at least one match in 2026 are ranked, and
players who have represented Pakistan / Pakistan A are not ranked. Excluded players are still rated on the same scale
(see "Show excluded" on the ranking pages).

## Project layout

```
superr_selector/
├── run_pipeline.py          # builds everything (about 1–2 minutes)
├── config/settings.py       # every weight, threshold and rule in one place
├── src/
│   ├── data_prep.py         # load, clean, de-duplicate, merge the six CSVs
│   ├── match_state.py       # targets, match state before every ball, player history before each match
│   ├── models.py            # resource table, win probability, expected outcomes (cross-fitted)
│   ├── pressure.py          # batting & bowling Pressure Index + 5 alternative definitions
│   ├── ratings.py           # impact consistency, value, uplift, shrinkage, reliability replicates
│   ├── validation.py        # tier checks and research-paper replications (P4, P6, P7)
│   ├── insights.py          # strong zones, situations, dismissals, match-ups, match logs
│   └── report.py            # writes reports/methodology_report.md + .docx from the outputs
├── app/                     # Streamlit dashboard (app.py, ui/, views/, assets/)
├── data/raw/                # the six supplied CSVs
├── data/processed/          # master_ball_by_ball.parquet (the single analytical file) + clean tables
├── outputs/                 # rankings, top-10 lists, replicates, validation and insight tables
└── reports/                 # methodology_report.md / .docx + figures
```

## Run it in PyCharm on Windows

1. **Unzip** `superr_selector.zip`, e.g. into `C:\Users\<you>\PycharmProjects\`.
2. **Open the project.** PyCharm → File → Open → select the `superr_selector` folder → Trust Project.
3. **Create an interpreter.** File → Settings → Project: superr_selector → Python Interpreter →
   Add Interpreter → Add Local Interpreter → Virtualenv Environment → New, base interpreter Python 3.10–3.13 → OK.
4. **Install packages.** Open the PyCharm Terminal (Alt+F12) and run:
   ```
   pip install -r requirements.txt
   ```
5. **(Optional) Rebuild the analysis.** Outputs are already included, so this is only needed after changing
   `config\settings.py` or the data:
   ```
   python run_pipeline.py
   ```
   `--fast` uses 60 replicates for a quick check; `--csv` also writes the master file as CSV.
6. **Launch the dashboard.** In the same terminal:
   ```
   streamlit run app/app.py
   ```
   Your browser opens at http://localhost:8501. Stop it with Ctrl+C.

   To launch from a Run button instead: Run → Edit Configurations → + → Python → switch "Script path" to
   **Module name** `streamlit`, Parameters `run app/app.py`, Working directory = the project folder.

## Where to find the answers

* `outputs/top10_batters.csv`, `outputs/top10_bowlers.csv` — the submission lists (rank 1–10).
* `outputs/batter_rankings.csv`, `outputs/bowler_rankings.csv` — every eligible player with all metrics.
* `reports/methodology_report.docx` — the methodology report for upload.
* Dashboard page **Most Reliable Players** — both lists, with replicate distributions and evidence.
* **Player Profiles** — whole-career profile of any player; **Player Explorer** — his pressure profile.
* **Methodology** — every attribute and calculation, with worked examples on real balls and real ratings.

## Deploy on Streamlit Community Cloud

The cloud app only sees what is in your GitHub repository. Running the pipeline in PyCharm creates the results on your
computer, but nothing reaches the cloud until it is committed and pushed.

1. **Run the pipeline locally** (`python run_pipeline.py`) so `outputs/` is up to date.
2. **Push the project to GitHub, including the `outputs/` folder.** The dashboard needs only `app/`, `config/`,
   `outputs/` (about 21 MB, every file under 25 MB), `.streamlit/` and `requirements.txt`.
   * `data/processed/` is listed in `.gitignore` because the dashboard doesn't use it.
   * `data/raw/ball_by_ball.csv` (41 MB) is too big to upload through the github.com web page (25 MB limit per
     file). Push it with git or GitHub Desktop (100 MB limit), or leave `data/raw/` out; the dashboard doesn't need it.
3. On share.streamlit.io → **Create app**: choose the repository and branch, and set **Main file path** to
   `app/app.py` (or `<subfolder>/app/app.py` if the project sits in a subfolder of the repository).
4. After pushing new results, open the app's menu (⋮) → **Reboot app**.

If a page says "Analytical output not found", it lists the folder it is reading and the exact files that are missing.
