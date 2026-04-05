# RoadToIvy

RoadToIvy is a PyCharm-ready Flask application that gives secondary-school students a serious admissions gap analysis for elite universities in the USA, Canada, UK, and Europe.

## What it does
- collects student age, gender, name, extracurriculars, grades, and target course
- benchmarks the profile against seeded elite university + program profiles
- distinguishes undergraduate targets from postgraduate-only pathways like Harvard Law J.D.
- returns a readiness score, verdict, and next-step roadmap
- uses a local SQLite database seeded from JSON so the project is fully portable

## Stack
- Python
- Flask
- SQLite
- HTML / CSS

## Run locally
1. Open the project in PyCharm.
2. Create a virtual environment.
3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   python run.py
   ```
5. Open the local URL shown in the terminal.

## Seed data model
The seed database includes elite or high-ranked universities across:
- USA
- Canada
- UK
- Switzerland
- Germany
- Netherlands
- France
- Ireland
- Belgium

Each program profile stores:
- course name and level
- academic threshold and stretch threshold
- extracurricular threshold
- required and recommended subjects
- tests or application components
- profile emphasis such as leadership, research, service, or work experience
- language notes for continental European pathways

## Important real-world note
This project is a strong MVP, not a legally complete admissions oracle. Real deployment should:
- refresh official admissions requirements on a schedule
- store evidence sources for every program profile
- add international qualification mapping by curriculum type (A-levels, IB, AP, Leaving Cert, etc.)
- add user accounts, admin data tools, audit logs, and privacy controls
- separate undergraduate, graduate, law, and medical pathways with more precision

## Suggested next upgrades
- add admin dashboard for editing university/program criteria
- attach source URLs and last-verified dates to each program record
- add curriculum-aware converters for A-level, IB, GPA, and percentage systems
- add essay/CV positioning recommendations by target school
- add probability bands and action timelines by age / school year
