# ORBIT — Curriculum Console + Module 4 Trainer

A clinical-workspace-styled Flask app for the **Oral Radiology Board-Interpretation Trainer**
(Dr. Perelman AIxEducation dental-radiology project).

- A curriculum **console** (overview, modules, case library, interaction matrix,
  reference) generated from `ORBIT Database (1).xlsx`.
- A fully **functioning Module 4 — Normal Anatomy vs Pathology** that a learner
  works through: 4 real trap cases (Mental Foramen, Cervical Burnout, Nutrient
  Canal, Maxillary Sinus), each with classify → identify → justify steps, scored
  feedback, a **live AI tutor** (objective 7), and a results screen mapping every
  answer back to the 7 learning objectives.

## Run it

```bash
cd orbit_dashboard
pip install -r requirements.txt
python build_data.py     # (re)generate data/orbit.json from the workbook
python app.py            # http://127.0.0.1:5001

FLASK_DEBUG=1 python app.py   # dev only: auto-reload + interactive debugger
```

`FLASK_DEBUG` is off by default — the Werkzeug debugger exposes an interactive
Python console, so it must never be on for a host reachable off the machine.

Then open **http://127.0.0.1:5001/module/4/practice** for the demo.

## The AI tutor

Module 4 objective 7 (improve after AI dialogue) is realized by the live **AI
Companion**. It uses `ANTHROPIC_API_KEY` from the environment, falling back to
the project's `.streamlit/secrets.toml`. If no key is present it degrades to a
scripted coach, so the demo never breaks.

## Layout

| Path | What it is |
|------|-----------|
| `build_data.py` | Workbook → normalized `data/orbit.json` |
| `data/module4_cases.json` | Authored interactive content for Module 4 |
| `app.py` | Flask routes incl. `/module/4/practice` and `/api/module4/tutor` |
| `templates/` | Jinja templates (ORBIT-styled) |
| `static/css/orbit.css` | ORBIT design system (tokens in `:root`) |
| `static/js/module4.js` | The Module 4 interactive engine |
