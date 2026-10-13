# 📷 PhotoGrade

**Version 1.0.0 — First Release**

PhotoGrade is a local-first Python desktop app that helps photography teachers evaluate student photos using EXIF metadata and configurable technical rules, then combine automated scores with teacher grading.

## ✨ Key Features

- **Class & Student Management** — Create and reopen classes, manage students, and add multiple photos from folders or individual files.
- **Technical Analysis** — Read EXIF metadata, inspect RGB histograms, and evaluate photos with configurable rules and tolerance.
- **Flexible Grading** — Combine Rule Engine and teacher scores with adjustable weights; add notes to individual photos.
- **Progress & Search** — Track completion, search classes and students, and save unfinished grading to continue later.
- **Results & Export** — Review class and per-student results, then export reports to Excel.
- **Presets & Settings** — Reuse grading rules and configure grading defaults and app preferences.
- **Drag & Drop** — Load images directly into the app.
- **Built-in Help** — Find workflow instructions inside the application.

## 📸 Screenshots

<table>
  <tr>
    <td align="center" width="50%"><strong>Home</strong></td>
    <td align="center" width="50%"><strong>Class Management</strong></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/images/home_page.png" alt="PhotoGrade Home" width="100%"></td>
    <td width="50%"><img src="assets/images/class_manager.png" alt="PhotoGrade Class Management" width="100%"></td>
  </tr>
  <tr>
    <td align="center" width="50%"><strong>Rule Engine</strong></td>
    <td align="center" width="50%"><strong>Grading Workflow</strong></td>
  </tr>
  <tr>
    <td width="50%"><img src="assets/images/rule_engine.png" alt="PhotoGrade Rule Engine" width="100%"></td>
    <td width="50%"><img src="assets/images/grading.png" alt="PhotoGrade Grading" width="100%"></td>
  </tr>
</table>

## 🏗️ Project Structure

```text
Photograde/
├── .github/workflows/     # Automated test workflow
├── app/
│   ├── core/              # Metadata, image analysis, rules, scoring, data models
│   ├── gui/               # Application screens, widgets, help and settings
│   └── storage/           # Class data, presets, settings, progress and exports
├── assets/images/         # README screenshots
├── tests/                 # Automated tests
├── main.py                # Application entry point
├── requirements.txt
└── README.md
```

Class data and unfinished grading progress are stored locally in the `classes/` directory during use.

## ▶️ Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start PhotoGrade:

```bash
python main.py
```

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

PhotoGrade uses Python, CustomTkinter, pandas, Pillow, piexif, and pytest.
