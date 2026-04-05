from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = BASE_DIR / "data" / "roadtoivy.db"
SEED_PATH = BASE_DIR / "data" / "seed_data.json"

app = Flask(__name__)


GRADE_MAPPINGS = {
    'A*': 98,
    'A+': 97,
    'A': 94,
    'A-': 91,
    'B+': 88,
    'B': 85,
    'B-': 81,
    'C+': 78,
    'C': 75,
    'C-': 71,
    'D': 65,
}


EXTRACURRICULAR_WEIGHTS = {
    'national_award': 12,
    'international_award': 15,
    'founder': 10,
    'research': 9,
    'olympiad': 10,
    'volunteering': 5,
    'sports_captain': 7,
    'music_grade': 4,
    'internship': 8,
    'debate': 6,
    'student_government': 5,
    'publication': 9,
}


SUBJECT_ALIASES = {
    'mathematics': {'math', 'mathematics', 'further maths', 'further math', 'calculus'},
    'physics': {'physics'},
    'chemistry': {'chemistry'},
    'biology': {'biology'},
    'english': {'english', 'english literature', 'language arts'},
    'computer science': {'computer science', 'cs', 'informatics'},
    'economics': {'economics'},
    'history': {'history'},
}


COUNTRY_REGIONS = {
    'USA': 'USA',
    'Canada': 'Canada',
    'UK': 'UK',
    'Switzerland': 'Europe',
    'France': 'Europe',
    'Netherlands': 'Europe',
    'Germany': 'Europe',
    'Ireland': 'Europe',
    'Belgium': 'Europe',
    'Denmark': 'Europe',
    'Sweden': 'Europe',
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS universities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            region TEXT NOT NULL,
            tier TEXT NOT NULL,
            ranking_band TEXT NOT NULL,
            acceptance_band TEXT NOT NULL,
            notes TEXT NOT NULL
        )
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_id INTEGER NOT NULL,
            program_name TEXT NOT NULL,
            level TEXT NOT NULL,
            field_group TEXT NOT NULL,
            min_avg REAL NOT NULL,
            stretch_avg REAL NOT NULL,
            min_ec_score REAL NOT NULL,
            stretch_ec_score REAL NOT NULL,
            required_subjects TEXT NOT NULL,
            recommended_subjects TEXT NOT NULL,
            required_tests TEXT NOT NULL,
            portfolio_required INTEGER NOT NULL,
            leadership_importance INTEGER NOT NULL,
            research_importance INTEGER NOT NULL,
            service_importance INTEGER NOT NULL,
            work_experience_importance INTEGER NOT NULL,
            postgraduate_only INTEGER NOT NULL,
            language_notes TEXT NOT NULL,
            profile_notes TEXT NOT NULL,
            FOREIGN KEY(university_id) REFERENCES universities(id)
        )
        '''
    )
    conn.commit()

    count = cur.execute('SELECT COUNT(*) FROM universities').fetchone()[0]
    if count == 0:
        seed = json.loads(SEED_PATH.read_text())
        for uni in seed['universities']:
            cur.execute(
                '''INSERT INTO universities(name, country, region, tier, ranking_band, acceptance_band, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (
                    uni['name'],
                    uni['country'],
                    COUNTRY_REGIONS.get(uni['country'], 'Europe'),
                    uni['tier'],
                    uni['ranking_band'],
                    uni['acceptance_band'],
                    uni['notes'],
                ),
            )
            university_id = cur.lastrowid
            for program in uni['programs']:
                cur.execute(
                    '''INSERT INTO programs(
                        university_id, program_name, level, field_group, min_avg, stretch_avg,
                        min_ec_score, stretch_ec_score, required_subjects, recommended_subjects,
                        required_tests, portfolio_required, leadership_importance, research_importance,
                        service_importance, work_experience_importance, postgraduate_only,
                        language_notes, profile_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        university_id,
                        program['program_name'],
                        program['level'],
                        program['field_group'],
                        program['min_avg'],
                        program['stretch_avg'],
                        program['min_ec_score'],
                        program['stretch_ec_score'],
                        json.dumps(program['required_subjects']),
                        json.dumps(program['recommended_subjects']),
                        json.dumps(program['required_tests']),
                        1 if program.get('portfolio_required') else 0,
                        program.get('leadership_importance', 3),
                        program.get('research_importance', 3),
                        program.get('service_importance', 2),
                        program.get('work_experience_importance', 1),
                        1 if program.get('postgraduate_only') else 0,
                        program.get('language_notes', ''),
                        program.get('profile_notes', ''),
                    ),
                )
        conn.commit()
    conn.close()


def normalize_subject(subject: str) -> str:
    lowered = subject.strip().lower()
    for canonical, aliases in SUBJECT_ALIASES.items():
        if lowered in aliases:
            return canonical
    return lowered


def parse_grade(value: str) -> float:
    raw = value.strip()
    if not raw:
        return 0.0
    if raw in GRADE_MAPPINGS:
        return float(GRADE_MAPPINGS[raw])
    try:
        return float(raw)
    except ValueError:
        return 0.0


def parse_subjects(text: str) -> Dict[str, float]:
    parsed: Dict[str, float] = {}
    for line in text.splitlines():
        if ':' not in line:
            continue
        subject, grade = line.split(':', 1)
        parsed[normalize_subject(subject)] = parse_grade(grade)
    return parsed


def parse_extracurriculars(text: str) -> List[str]:
    return [item.strip().lower() for item in text.replace(';', '\n').splitlines() if item.strip()]


def extracurricular_score(items: List[str]) -> float:
    total = 0.0
    for item in items:
        added = False
        for key, weight in EXTRACURRICULAR_WEIGHTS.items():
            if key.replace('_', ' ') in item or key in item:
                total += weight
                added = True
                break
        if not added:
            total += 3
    return min(total, 50.0)


def find_best_program_match(course: str) -> List[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        '''
        SELECT p.*, u.name AS university_name, u.country, u.tier, u.ranking_band, u.acceptance_band, u.notes AS university_notes
        FROM programs p
        JOIN universities u ON p.university_id = u.id
        WHERE lower(p.program_name) LIKE ? OR lower(p.field_group) LIKE ?
        ORDER BY CASE u.tier
            WHEN 'A1' THEN 1
            WHEN 'A2' THEN 2
            WHEN 'B1' THEN 3
            ELSE 4 END,
            p.stretch_avg DESC
        ''',
        (f"%{course.lower()}%", f"%{course.lower()}%"),
    ).fetchall()
    conn.close()
    return rows


def score_program(student: Dict[str, Any], program: sqlite3.Row) -> Dict[str, Any]:
    grades = student['grades']
    avg = sum(grades.values()) / len(grades) if grades else 0.0
    ec_score = extracurricular_score(student['extracurriculars'])

    required_subjects = json.loads(program['required_subjects'])
    recommended_subjects = json.loads(program['recommended_subjects'])
    required_tests = json.loads(program['required_tests'])

    subject_hits = []
    missing_subjects = []
    weak_subjects = []
    for subject in required_subjects:
        canonical = normalize_subject(subject)
        grade = grades.get(canonical)
        if grade is None:
            missing_subjects.append(subject)
        else:
            subject_hits.append(subject)
            if grade < max(program['min_avg'] - 3, 85):
                weak_subjects.append(f'{subject} ({grade:.0f})')

    recommended_hits = []
    for subject in recommended_subjects:
        if normalize_subject(subject) in grades:
            recommended_hits.append(subject)

    avg_gap = round(program['stretch_avg'] - avg, 1)
    ec_gap = round(program['stretch_ec_score'] - ec_score, 1)

    academic_score = max(0, min(100, 100 - max(0, avg_gap) * 5))
    activities_score = max(0, min(100, 100 - max(0, ec_gap) * 4))
    subject_score = max(0, 100 - len(missing_subjects) * 25 - len(weak_subjects) * 8)

    readiness = round((academic_score * 0.5) + (activities_score * 0.25) + (subject_score * 0.25), 1)

    if program['postgraduate_only']:
        readiness = min(readiness, 45)

    if readiness >= 82:
        verdict = 'Competitive stretch'
    elif readiness >= 68:
        verdict = 'Possible with upgrades'
    elif readiness >= 50:
        verdict = 'Currently off pace'
    else:
        verdict = 'Not yet viable'

    next_steps: List[str] = []
    if program['postgraduate_only']:
        next_steps.append('This target is postgraduate-only. You would first need a strong undergraduate degree before applying.')
    if avg < program['stretch_avg']:
        next_steps.append(f'Lift academic average from {avg:.1f} toward {program["stretch_avg"]:.0f}+ for realistic contention.')
    if missing_subjects:
        next_steps.append('Add or prove strength in required subjects: ' + ', '.join(missing_subjects) + '.')
    if weak_subjects:
        next_steps.append('Upgrade weak core subjects: ' + ', '.join(weak_subjects) + '.')
    if ec_score < program['stretch_ec_score']:
        next_steps.append('Build a more credible extracurricular profile with leadership, research, competition results, or impact.')
    if required_tests:
        next_steps.append('Plan for required tests/components: ' + ', '.join(required_tests) + '.')
    if program['portfolio_required']:
        next_steps.append('Prepare a serious portfolio or project body of work.')
    if not next_steps:
        next_steps.append('Maintain grades, tighten narrative, and execute applications with precise positioning.')

    profile_focus = []
    if program['leadership_importance'] >= 4:
        profile_focus.append('leadership')
    if program['research_importance'] >= 4:
        profile_focus.append('research')
    if program['service_importance'] >= 4:
        profile_focus.append('service')
    if program['work_experience_importance'] >= 4:
        profile_focus.append('work experience')

    return {
        'university_name': program['university_name'],
        'country': program['country'],
        'tier': program['tier'],
        'program_name': program['program_name'],
        'level': program['level'],
        'ranking_band': program['ranking_band'],
        'acceptance_band': program['acceptance_band'],
        'readiness': readiness,
        'verdict': verdict,
        'avg': round(avg, 1),
        'target_avg': program['stretch_avg'],
        'ec_score': round(ec_score, 1),
        'target_ec': program['stretch_ec_score'],
        'missing_subjects': missing_subjects,
        'recommended_hits': recommended_hits,
        'required_tests': required_tests,
        'profile_focus': profile_focus,
        'language_notes': program['language_notes'],
        'profile_notes': program['profile_notes'],
        'university_notes': program['university_notes'],
        'next_steps': next_steps,
    }


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    student = {
        'name': request.form.get('name', '').strip(),
        'age': request.form.get('age', '').strip(),
        'gender': request.form.get('gender', '').strip(),
        'course': request.form.get('course', '').strip(),
        'grades': parse_subjects(request.form.get('grades', '')),
        'extracurriculars': parse_extracurriculars(request.form.get('extracurriculars', '')),
    }

    course = student['course']
    matches = find_best_program_match(course)
    if not matches:
        return render_template('index.html', error='No matching programs found. Try a broader course label such as computer science, economics, law, engineering, medicine, or design.')

    scored = [score_program(student, row) for row in matches[:12]]
    scored.sort(key=lambda item: item['readiness'], reverse=True)
    dream = scored[0]
    reach = [item for item in scored if item['tier'] in {'A1', 'A2'}][:5]
    strong_alternatives = [item for item in scored if item['readiness'] >= 60][:5]

    return render_template(
        'results.html',
        student=student,
        dream=dream,
        reach=reach,
        strong_alternatives=strong_alternatives,
        scored=scored,
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
