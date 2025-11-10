#!/usr/bin/env bash
set -euo pipefail
set -o pipefail

# ========= Config =========
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_DIR="$REPO_ROOT/backend/tests/integration"
OUT_DIR="$REPO_ROOT/backend/tests/reports"
REPORT_PREFIX="integration"
HTTP_SUMMARY="$OUT_DIR/junit_http_summary_${REPORT_PREFIX}.txt"
JUNIT_XML="$OUT_DIR/junit_${REPORT_PREFIX}.xml"
COV_XML="$OUT_DIR/coverage_${REPORT_PREFIX}.xml"
COV_HTML_DIR="$OUT_DIR/htmlcov_${REPORT_PREFIX}"
LOG_FILE="$OUT_DIR/pytest_${REPORT_PREFIX}_output.txt"
SUMMARY_FILE="$OUT_DIR/summary_${REPORT_PREFIX}.txt"
SUMMARY_JSON="$OUT_DIR/summary_${REPORT_PREFIX}.json"
MD_REPORT="$OUT_DIR/report_${REPORT_PREFIX}.md"
JSON_REPORT="$OUT_DIR/report_${REPORT_PREFIX}.json"
DURATIONS_N="${DURATIONS_N:-10}"
COV_MIN="${COV_MIN:-}"

# Ensure output dir exists
mkdir -p "$OUT_DIR"

# Sync tests requirements into backend/requirements.txt if available
TEST_REQ="$REPO_ROOT/backend/tests/requirements.txt"
MAIN_REQ="$REPO_ROOT/backend/requirements.txt"
if [[ -f "$TEST_REQ" && -f "$MAIN_REQ" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if ! grep -Fqx "$line" "$MAIN_REQ"; then
      echo "$line" >> "$MAIN_REQ"
    fi
  done < "$TEST_REQ"
fi

# Make sure Python can import backend/app package (for potential helpers)
export PYTHONPATH="$REPO_ROOT/backend:${PYTHONPATH:-}"

# ========= Banner =========
echo "[run_${REPORT_PREFIX}] Starting ${REPORT_PREFIX} tests"
echo "[run_${REPORT_PREFIX}] TEST_DIR=$TEST_DIR"
echo "[run_${REPORT_PREFIX}] OUT_DIR=$OUT_DIR"

# ========= Plugin detection =========
HAVE_PYTEST_COV=0
python - <<'PY' >/dev/null 2>&1 || true
import importlib, sys
try:
    importlib.import_module('pytest_cov')
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
if [[ $? -eq 0 ]]; then HAVE_PYTEST_COV=1; fi

HAVE_PYTEST_JSON=0
python - <<'PY' >/dev/null 2>&1 || true
import importlib, sys
try:
    importlib.import_module('pytest_jsonreport')
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
if [[ $? -eq 0 ]]; then HAVE_PYTEST_JSON=1; fi

# ========= Build pytest args =========
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTEST_HTTP_REPORT_PATH="$HTTP_SUMMARY"

PYTEST_ARGS=(
  "$TEST_DIR"
  -vv -rA                     # per-file, per-test method verbose output
  --durations="$DURATIONS_N"  # show slow tests
  -o console_output_style=classic
  --junitxml "$JUNIT_XML"
  -W ignore::DeprecationWarning
)

# Note: Integration tests use remote HTTP by default; coverage for backend code
# may be minimal unless tests import code. Still expose coverage if plugin exists.
if [[ "$HAVE_PYTEST_COV" == "1" ]]; then
  echo "[run_${REPORT_PREFIX}] pytest-cov detected: enabling coverage"
  PYTEST_ARGS+=(
    -p pytest_cov
    --cov=backend/app/routes
    --cov=backend/app/services
    --cov=backend/app/utils
    --cov=backend/app/core
    --cov-report=term-missing
    --cov-report=xml:"$COV_XML"
    --cov-report=html:"$COV_HTML_DIR"
  )
  if [[ -n "$COV_MIN" ]]; then
    PYTEST_ARGS+=( --cov-fail-under="$COV_MIN" )
  fi
else
  echo "[run_${REPORT_PREFIX}] pytest-cov not available: running without coverage"
fi

if [[ "$HAVE_PYTEST_JSON" == "1" ]]; then
  echo "[run_${REPORT_PREFIX}] pytest-json-report detected: enabling JSON report"
  PYTEST_ARGS+=( -p pytest_jsonreport --json-report --json-report-file="$JSON_REPORT" --json-report-omit=environment,cwd,python,platform,summary )
fi

# Pass through any extra args to pytest
if [[ $# -gt 0 ]]; then
  echo "[run_${REPORT_PREFIX}] Extra pytest args: $*"
  PYTEST_ARGS+=( "$@" )
fi

# ========= Run pytest (keep going to print summary even on failures) =========
set +e
pytest "${PYTEST_ARGS[@]}" | tee "$LOG_FILE"
PYTEST_STATUS=${PIPESTATUS[0]}
set -e

# ========= Post-process: compute totals and coverage, print and save =========
python - "$JUNIT_XML" "$COV_XML" "$SUMMARY_FILE" "$SUMMARY_JSON" "$MD_REPORT" "$REPORT_PREFIX" "$COV_HTML_DIR" <<'PY'
import sys, os, re, json
from xml.etree import ElementTree as ET
from datetime import datetime, timezone
from app.utils.tools import UTC8

junit_xml, cov_xml, summary_file, summary_json, md_report, prefix, cov_html_dir = sys.argv[1:8]

cases=0; failures=0; errors=0; skipped=0; passed=0
methods=set(); modules=set(); per_case=[]

if os.path.exists(junit_xml):
    try:
        tree=ET.parse(junit_xml)
        root=tree.getroot()
        testcases = root.findall('.//testcase') if root.tag!='testcase' else [root]
        for tc in testcases:
            cases += 1
            name = tc.get('name') or ''
            classname = tc.get('classname') or ''
            time = float(tc.get('time') or 0.0)
            status = 'passed'
            if tc.find('failure') is not None:
                failures += 1; status='failed'
            elif tc.find('error') is not None:
                errors += 1; status='error'
            elif tc.find('skipped') is not None:
                skipped += 1; status='skipped'
            else:
                passed += 1
            if name:
                name = re.sub(r"\[.*\]$", "", name)
                methods.add(f"{classname}::{name}" if classname else name)
            if classname:
                modules.add(classname)
            per_case.append({'name': name,'classname': classname,'time': time,'status': status})
    except Exception as e:
        print(f"[summary] Failed to parse junit xml: {e}")

coverage_pct = None
if os.path.exists(cov_xml):
    try:
        tree=ET.parse(cov_xml)
        root=tree.getroot()
        line_rate = root.get('line-rate')
        if line_rate is not None:
            coverage_pct = round(float(line_rate)*100.0, 2)
    except Exception as e:
        print(f"[summary] Failed to parse coverage xml: {e}")

summary_line = (
    f"SUMMARY: files={len(modules)} methods={len(methods)} cases={cases} "
    f"passed={passed} failed={failures} errors={errors} skipped={skipped} "
    f"coverage={(str(coverage_pct)+'%') if coverage_pct is not None else 'N/A'}"
)
print(summary_line)

# plaintext
try:
    with open(summary_file,'w',encoding='utf-8') as f:
        f.write(summary_line+"\n")
except Exception as e:
    print(f"[summary] Failed to write {summary_file}: {e}")

# json
try:
    with open(summary_json,'w',encoding='utf-8') as f:
        json.dump({'files': len(modules),'methods': len(methods),'cases': cases,'passed': passed,'failed': failures,'errors': errors,'skipped': skipped,'coverage_percent': coverage_pct,'generated_at': datetime.now(timezone.utc).isoformat(),'prefix': prefix}, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(f"[summary] Failed to write {summary_json}: {e}")

# markdown
try:
    slow = sorted(per_case, key=lambda x: x['time'], reverse=True)[:10]
    lines = []
    lines.append(f"# Test Report ({prefix})\n")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
    lines.append("## Summary\n")
    lines.append(f"- Files (modules): {len(modules)}\n")
    lines.append(f"- Methods: {len(methods)}\n")
    lines.append(f"- Cases: {cases}\n")
    lines.append(f"- Passed: {passed}\n")
    lines.append(f"- Failed: {failures}\n")
    lines.append(f"- Errors: {errors}\n")
    lines.append(f"- Skipped: {skipped}\n")
    lines.append(f"- Coverage: {(str(coverage_pct)+'%') if coverage_pct is not None else 'N/A'}\n")
    if os.path.isdir(cov_html_dir):
        lines.append(f"- Coverage HTML: {cov_html_dir}\n")
    lines.append("\n## Slowest tests (top 10)\n")
    lines.append("| # | Test | Time (s) | Status |\n|---|------|----------:|--------|\n")
    for i, t in enumerate(slow, start=1):
        full = f"{t['classname']}::{t['name']}" if t['classname'] else t['name']
        lines.append(f"| {i} | {full} | {t['time']:.3f} | {t['status']} |\n")
    lines.append("\n## Artifacts\n")
    lines.append(f"- JUnit XML: {junit_xml}\n")
    if os.path.exists(cov_xml):
        lines.append(f"- Coverage XML: {cov_xml}\n")
    lines.append(f"- Pytest log: {os.path.join(os.path.dirname(junit_xml), 'pytest_'+prefix+'_output.txt')}\n")
    http_sum = os.path.join(os.path.dirname(junit_xml), 'junit_http_summary_'+prefix+'.txt')
    if os.path.exists(http_sum):
        lines.append(f"- HTTP Summary: {http_sum}\n")
    if os.path.exists(os.path.join(os.path.dirname(junit_xml), 'report_'+prefix+'.json')):
        lines.append(f"- JSON Report: {os.path.join(os.path.dirname(junit_xml), 'report_'+prefix+'.json')}\n")
    with open(md_report,'w',encoding='utf-8') as f:
        f.write(''.join(lines))
except Exception as e:
    print(f"[summary] Failed to write {md_report}: {e}")
PY

# ========= Exit status =========
if [[ $PYTEST_STATUS -ne 0 ]]; then
  echo "[run_${REPORT_PREFIX}] pytest exited with status $PYTEST_STATUS"
  exit $PYTEST_STATUS
fi

echo "[run_${REPORT_PREFIX}] Done"
