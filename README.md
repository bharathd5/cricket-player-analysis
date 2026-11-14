SupeRR Selector Season 2 — Most Reliable Players Under Pressure
A data-driven system that scores every IPL and T20I delivery (2022–2026) for batting pressure and bowling pressure, measures each player against an average player in the same situation and against his own usual level, and ranks the players who deliver most consistently when it matters. It includes SUPERR INTELLIGENCE, a 9-page Streamlit dashboard.

Project layout
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
Run it in PyCharm on Windows
Unzip superr_selector.zip, e.g. into C:\Users\<you>\PycharmProjects.

Open the project. PyCharm → File → Open → select the superr_selector folder → Trust Project.

Create an interpreter. File → Settings → Project: superr_selector → Python Interpreter → Add Interpreter → Add Local Interpreter → Virtualenv Environment → New, base interpreter Python 3.10–3.13 → OK.

Install packages. Open the PyCharm Terminal (Alt+F12) and run:

pip install -r requirements.txt
(Optional) Rebuild the analysis. Outputs are already included, so this is only needed after changing config\settings.py or the data:

python run_pipeline.py
--fast uses 60 replicates for a quick check; --csv also writes the master file as CSV.

Launch the dashboard. In the same terminal:

streamlit run app/app.py
Your browser opens at http://localhost:8501. Stop it with Ctrl+C.

To launch from a Run button instead: Run → Edit Configurations → + → Python → switch "Script path" to Module name streamlit, Parameters run app/app.py, Working directory = the project folder.

Where to find the answers
outputs/top10_batters.csv, outputs/top10_bowlers.csv — the submission lists (rank 1–10).
outputs/batter_rankings.csv, outputs/bowler_rankings.csv — every eligible player with all metrics.
reports/methodology_report.docx — the methodology report for upload.
Dashboard page Most Reliable Players — both lists, with replicate distributions and evidence.
