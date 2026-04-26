# Code Review — pullup-calculator

**Reviewer:** Senior Software Developer  
**Date:** 2025-07-18  
**Scope:** Full repository review (neatness, modularity, security)

---

## Overall Impression

This is a well-structured, focused personal project. The architecture (GitHub → Render → Neon) is cleanly documented, the calculation logic is correctly separated from the web layer, and the dual-backend database abstraction (Postgres + local JSON) is a nice touch. The README is excellent. That said, there are a few issues — one critical — that should be addressed.

---

## 🔴🟡🟢 Findings

---

### 1. Security

#### 🔴 S1 — Database credentials committed to `.env` in repository

**File:** `.env` (line 1)

The `.env` file contains a **live PostgreSQL connection string** with username and password in plaintext. Although `.env` is listed in `.gitignore`, the file is currently present in the working tree and — if ever accidentally committed — would expose credentials in Git history permanently. **The credentials visible in `.env` should be rotated immediately** regardless, since anyone with access to the working copy can see them.

**Recommendation:** Never store real credentials in the repo directory. Use a system-level environment variable, a secrets manager, or a `.env.local` file that is never committed. Add a `.env.example` with placeholder values instead.

---

#### 🔴 S2 — Hardcoded fallback secret key

**File:** `app.py` (line 19)

```python
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
```

If `SECRET_KEY` is not set (e.g. during local development), the app runs with a predictable, hardcoded secret. Flask session cookies are signed with this key — an attacker who knows it can forge session cookies, bypassing the `login_required` guard entirely.

**Recommendation:** Raise an error in production if `SECRET_KEY` is not set, or at minimum generate a random key at startup for local dev:

```python
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32).hex()
```

---

#### 🟡 S3 — Open redirect via `next` parameter

**File:** `app.py` (lines 42, 383)

```python
return redirect(url_for("login", next=request.url))
# ... and later ...
return redirect(request.args.get("next", url_for("timeline")))
```

The `next` query parameter is taken directly from the request and used in a redirect without validation. An attacker could craft a login URL like `/login?next=https://evil.com` to redirect users to a malicious site after authentication.

**Recommendation:** Validate that the `next` URL is relative (starts with `/` and not `//`):

```python
next_url = request.args.get("next", "")
if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
    next_url = url_for("timeline")
return redirect(next_url)
```

---

#### 🟡 S4 — No CSRF protection on forms

**Files:** `app.py`, `templates/index.html`, `templates/login.html`

None of the POST forms include CSRF tokens. An attacker could craft a page that submits a form to `/timeline` (adding/deleting entries) while the user is authenticated.

**Recommendation:** Integrate `Flask-WTF` or add manual CSRF token checking. At minimum, use the `SameSite` cookie attribute (Flask 2+ defaults to `Lax`, which mitigates but doesn't eliminate the risk).

---

#### 🟡 S5 — Password hash stored as plain environment variable

**File:** `app.py` (line 24)

`TIMELINE_PASSWORD` is loaded from the environment and compared with `check_password_hash`. This is actually a **good pattern** (storing a hash, not plaintext). However, if someone sets this variable to a plain-text password instead of a Werkzeug hash, `check_password_hash` will never match and the login will simply be permanently broken, with no error message explaining why. There is no validation or documentation on the expected format.

**Recommendation:** Add a startup check that validates the hash format, or document the expected format clearly (e.g. in `render.yaml` or README).

---

#### 🟢 S6 — No rate limiting on login

**File:** `app.py` (line 377–385)

The `/login` endpoint has no rate limiting or account lockout. An attacker can brute-force passwords without restriction.

**Recommendation:** Add `Flask-Limiter` or similar rate limiting on the login route.

---

#### 🟢 S7 — Debug mode enabled in `__main__`

**File:** `app.py` (line 436)

```python
app.run(debug=True, port=5050)
```

Debug mode is enabled when running directly. This is fine for local development and won't affect production (which uses gunicorn), but worth noting.

---

#### 🟢 S8 — Logout uses GET instead of POST

**File:** `app.py` (line 388–391)

The `/logout` route accepts GET requests, which means a simple `<img src="/logout">` tag could log a user out.

**Recommendation:** Use POST for state-changing operations.

---

### 2. Neatness

#### 🟡 N1 — Duplicate import of `check_password_hash`

**File:** `app.py` (lines 12 and 22)

```python
from werkzeug.security import check_password_hash  # line 12
# ...
from werkzeug.security import check_password_hash  # line 22
```

The same import appears twice. Remove the duplicate on line 22.

---

#### 🟡 N2 — Duplicate import of `date` alias inside function body

**File:** `app.py` (lines 268 and 309)

```python
from datetime import date as date_cls, timedelta  # line 268
# ... later in the same function ...
from datetime import date as date_cls  # line 309
```

`date_cls` is imported twice inside `build_timeline_charts`. The second import (line 309) is redundant. Also, `date` is already imported at module level (line 5), so neither inline import is necessary — just use the module-level import and alias it once at the top if needed.

---

#### 🟡 N3 — Inline imports of matplotlib inside helper function

**File:** `app.py` (lines 55–57)

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
```

These imports are inside `_extract_contour_paths`. While this avoids loading matplotlib at startup (a valid optimization), it means `matplotlib.use("Agg")` is called on every invocation. Consider importing at the module level with a comment explaining the choice, or caching the import.

---

#### 🟡 N4 — `app.py` is doing too many things for one file (~436 lines)

**File:** `app.py`

This file contains: Flask app setup, auth logic, four chart-building functions (heatmap, line chart, marginal reps chart, timeline charts), and all route handlers. For a personal project this is acceptable, but it's the main area where the codebase is starting to strain.

**Recommendation:** See Modularity section below.

---

#### 🟢 N5 — Magic numbers for chart configuration

**File:** `app.py` (lines 26, 129, 130, 174)

`CONTOUR_LEVELS`, `LINE_CHART_WEIGHTS`, `WEIGHT_COLORS`, and the inline `(8, "#9b59b6"), (11, "#3498db")` in `build_marginal_reps_chart` are scattered across the file. The first three are properly named as constants (good), but the inline tuples on line 174 should be given the same treatment.

---

#### 🟢 N6 — Hardcoded bodyweight default

**File:** `app.py` (lines 131, 352) and `templates/index.html` (line 131)

The default bodyweight of `64.0` appears in `app.py` and `64` appears as a hardcoded value in the HTML template. These should be a single constant.

---

#### 🟢 N7 — Inconsistent style in CSS

**File:** `templates/index.html` (lines 9–66)

The CSS is tightly compressed on single lines. This is a stylistic choice, but mixed with multi-line rules elsewhere it creates inconsistency. Consider using a consistent formatting style or extracting to a separate CSS file.

---

### 3. Modularity

#### 🟡 M1 — Chart-building logic lives in the web layer

**File:** `app.py` (lines 51–343)

Four chart-building functions (~290 lines) dominate `app.py`. These functions are pure data-to-JSON transformations with no dependency on Flask and could be extracted to a `charts.py` module. This would make `app.py` a thin routing layer and make chart logic independently testable.

**Recommendation:**
```
charts.py    → build_heatmap, build_line_chart, build_marginal_reps_chart, build_timeline_charts
app.py       → routes, auth, app config only
```

---

#### 🟡 M2 — `compute_1rm_grid` called redundantly

**File:** `app.py` (line 135)

```python
_, reps, _ = compute_1rm_grid(bodyweight)
```

`build_line_chart` calls `compute_1rm_grid` only to extract the `reps` array, then recomputes 1RM values individually in a loop. This throws away the grid and duplicates work. Consider reusing the grid or just creating the reps range directly with `np.arange`.

---

#### 🟡 M3 — The index route rebuilds charts twice on error

**File:** `app.py` (lines 351–374)

On POST, charts are first built with the default bodyweight (lines 354–356), then rebuilt inside the `try` block (lines 361–363), and rebuilt *again* in the `except` block (lines 366–368). The pre-POST builds on lines 354–356 are always wasted when the method is POST.

**Recommendation:** Build charts once, after determining the final bodyweight:

```python
bodyweight = default_bw
if request.method == "POST":
    try:
        bodyweight = float(request.form.get("bodyweight", ""))
    except (ValueError, TypeError):
        pass
plot_json = build_heatmap(bodyweight)
# ...
```

---

#### 🟢 M4 — Local JSON delete uses list index (fragile)

**File:** `db.py` (lines 89–92)

```python
def _local_delete(index: int) -> None:
    entries = _local_load()
    entries.pop(index)
```

Deleting by list index is fragile — if two users (or browser tabs) load the page and one deletes an entry, the indices shift and the second deletion could remove the wrong entry. In production (Postgres) this is fine because it uses row IDs, but the local fallback has this race condition.

**Recommendation:** Use an ID-based approach for local storage too, or accept this as a known limitation of the dev-only fallback.

---

#### 🟢 M5 — No input validation on date format

**File:** `app.py` (line 406)

```python
"date": request.form["date"],
```

The date string from the form is stored directly without validating it's a proper ISO date. The HTML `<input type="date">` provides client-side enforcement, but server-side validation is missing.

---

#### 🟢 M6 — `db.py` creates connection per operation

**File:** `db.py` (lines 30–31)

Each database operation opens a new connection. For a low-traffic personal app this is fine, but for scale you'd want connection pooling (e.g. via `psycopg2.pool` or SQLAlchemy).

---

#### 🟢 M7 — No tests

There are no unit tests or integration tests anywhere in the repository. The calculator logic in `calculator.py` is pure and easily testable.

---

## ✅ Good Practices

- **Clean separation of calculator logic** — `calculator.py` is focused, well-documented, and has clear docstrings with the formula derivation.
- **Parameterised SQL queries** — `db.py` uses `%s` placeholders throughout, preventing SQL injection. Well done.
- **Dual-backend storage** — The Postgres/JSON fallback in `db.py` is a pragmatic design that makes local development frictionless.
- **Jinja autoescaping** — Flask's default autoescaping mitigates XSS for rendered variables (e.g. `{{ message }}`, `{{ error }}`). The `| safe` usage on chart JSON is acceptable since it's server-generated.
- **Render deployment config** — `render.yaml` correctly generates `SECRET_KEY` and separates secrets.
- **CI/CD workflow** — The GitHub Actions workflow for syncing data is well-constructed with proper secret handling.
- **Excellent README** — Clear architecture diagram, environment variable docs, and project structure.
- **`.gitignore` covers `.env`** — The right intent is there, even if the file exists locally.

---

## Summary

| Severity | Count | Key Items |
|----------|-------|-----------|
| 🔴 Critical | 2 | Credentials in `.env`, hardcoded secret key |
| 🟡 Medium | 7 | Open redirect, no CSRF, duplicate imports, chart code in app.py, redundant chart builds |
| 🟢 Low | 8 | No rate limiting, debug mode, magic numbers, no tests |

The two critical issues (S1, S2) should be addressed immediately. The medium-severity items are worth fixing in the next iteration. The low-severity items are suggestions for improvement as the project grows.
