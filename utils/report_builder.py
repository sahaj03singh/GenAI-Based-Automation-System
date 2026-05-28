"""
report_builder.py — Generates a professional HTML test report.

Place this file at: utils/report_builder.py

Strict-mode features:
- Three test outcomes: PASS / PASS_WITH_HEALING / FAIL
- Per-step screenshot embedded inline (click to enlarge)
- Per-step confidence bar
- Per-step status badge (PASS / FAIL / WARN / HEALED)
- Summary dashboard with healed-test counts
- Collapsible test case cards
- Dark theme, clean typography
"""

import os
import base64
from datetime import datetime


def _encode_screenshot(path):
    """Encode a screenshot file to base64 for inline HTML embedding."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def _parse_step(step_entry):
    """
    Normalise a step_log entry.

    Accepts either:
      - A plain string:  "[PASS] click -> login button (conf: 0.94)"
      - A rich dict:     {"log": "...", "status": "PASS", ...}
    """
    if isinstance(step_entry, dict):
        status     = step_entry.get("status", "unknown").lower()
        action     = step_entry.get("action", "")
        target     = step_entry.get("target", step_entry.get("log", ""))
        confidence = step_entry.get("confidence", "")
        screenshot = step_entry.get("screenshot")
        return {
            "status":     status,
            "action":     action,
            "target":     target,
            "confidence": str(confidence) if confidence != "" else "",
            "screenshot": screenshot,
        }

    log = str(step_entry)
    if   "[PASS]"   in log: status = "pass"
    elif "[FAIL]"   in log: status = "fail"
    elif "[WARN]"   in log: status = "warn"
    elif "[HEALED]" in log: status = "healed"
    else:                    status = "unknown"

    content = log
    for prefix in ["[PASS] ", "[FAIL] ", "[WARN] ", "[HEALED] "]:
        content = content.replace(prefix, "")

    confidence = ""
    if "(conf:" in content:
        parts      = content.split("(conf:")
        content    = parts[0].strip()
        confidence = parts[1].replace(")", "").strip()

    action, target = "", content
    if "->" in content:
        parts  = content.split("->", 1)
        action = parts[0].strip()
        target = parts[1].strip()
    elif ":" in content:
        parts  = content.split(":", 1)
        action = parts[0].strip()
        target = parts[1].strip()

    return {
        "status":     status,
        "action":     action,
        "target":     target,
        "confidence": confidence,
        "screenshot": None,
    }


def _resolve_test_status(result):
    """
    Determine the strict test status.

    Returns one of: "PASS", "PASS_WITH_HEALING", "FAIL"
    Backward-compatible: if "status" key absent, falls back to
    the boolean "passed" field (treats it as PASS or FAIL).
    """
    if "status" in result:
        return result["status"]

    # Backward compat for old runs
    if result.get("passed"):
        # Check if any step was healed
        for log in result.get("step_logs", []):
            if isinstance(log, dict):
                if log.get("status", "").upper() == "HEALED":
                    return "PASS_WITH_HEALING"
            elif isinstance(log, str) and "[HEALED]" in log:
                return "PASS_WITH_HEALING"
        return "PASS"
    return "FAIL"


def generate_html_report(all_results, output_dir="reports"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(output_dir, f"report_{timestamp}.html")

    # ── Compute strict-mode statistics ────────────────────────────
    total_tests      = len(all_results)
    truly_passed     = 0
    passed_w_healing = 0
    failed_tests     = 0

    for r in all_results:
        st = _resolve_test_status(r)
        if   st == "PASS":              truly_passed     += 1
        elif st == "PASS_WITH_HEALING": passed_w_healing += 1
        else:                            failed_tests     += 1

    avg_conf = (
        sum(r.get("confidence", 0) for r in all_results) / total_tests
        if total_tests else 0
    )
    total_steps  = sum(
        r.get("details", {}).get("total_steps",  0) for r in all_results
    )
    passed_steps = sum(
        r.get("details", {}).get("steps_passed", 0) for r in all_results
    )
    healed_steps = sum(
        r.get("details", {}).get("steps_healed", 0) for r in all_results
    )
    # Backward compat — count from step_logs if details missing
    if healed_steps == 0:
        healed_steps = sum(
            1 for r in all_results
            for log in r.get("step_logs", [])
            if (
                (isinstance(log, dict)
                 and log.get("status", "").upper() == "HEALED")
                or (isinstance(log, str) and "[HEALED]" in log)
            )
        )

    run_time = datetime.now().strftime("%d %B %Y at %H:%M:%S")

    # ── Build test case HTML ──────────────────────────────────────
    test_blocks = ""
    for idx, result in enumerate(all_results):
        name       = result.get("name", f"Test {idx+1}")
        confidence = result.get("confidence", 0)
        step_logs  = result.get("step_logs", [])
        details    = result.get("details", {})

        # Determine card visual status from strict status
        test_status = _resolve_test_status(result)
        if test_status == "PASS":
            tc_class = "pass"
            tc_icon  = "&#10003;"
            tc_label = "PASS"
        elif test_status == "PASS_WITH_HEALING":
            tc_class = "warn"
            tc_icon  = "&#9888;"
            tc_label = "PASS (HEALED)"
        else:
            tc_class = "fail"
            tc_icon  = "&#10007;"
            tc_label = "FAIL"

        conf_pct   = int(confidence * 100)
        conf_color = (
            "#22d99a" if conf_pct >= 80
            else "#fbbf24" if conf_pct >= 60
            else "#f87171"
        )

        # ── Build per-step rows ───────────────────────────────────
        steps_html = ""
        for i, log_entry in enumerate(step_logs):
            parsed     = _parse_step(log_entry)
            st         = parsed["status"]
            screenshot = parsed.get("screenshot")
            img_b64    = _encode_screenshot(screenshot)

            badge_map = {
                "pass":    '<span class="badge bp">&#10003; PASS</span>',
                "fail":    '<span class="badge bf">&#10007; FAIL</span>',
                "warn":    '<span class="badge bw">&#9888; WARN</span>',
                "healed":  '<span class="badge bh">&#10041; HEALED</span>',
                "unknown": '<span class="badge bu">&#8212; &#8212;</span>',
            }
            status_badge = badge_map.get(st, badge_map["unknown"])

            conf_val = parsed["confidence"]
            try:
                cn  = float(conf_val)
                cbw = int(cn * 100)
                cc  = (
                    "#22d99a" if cn >= 0.8
                    else "#fbbf24" if cn >= 0.6
                    else "#f87171"
                )
                conf_cell = (
                    f'<div class="cw">'
                    f'<div class="cb" style="width:{cbw}%;'
                    f'background:{cc};"></div>'
                    f'<span class="cn">{conf_val}</span>'
                    f'</div>'
                )
            except Exception:
                conf_cell = (
                    f'<span class="cn">'
                    f'{conf_val if conf_val else "—"}</span>'
                )

            if img_b64:
                img_cell = (
                    f'<div class="tw">'
                    f'<img class="th" src="data:image/png;base64,{img_b64}" '
                    f'alt="Step {i+1}" onclick="openModal(this.src)" '
                    f'title="Step {i+1} — click to enlarge"/>'
                    f'<span class="tl">step {i+1}</span>'
                    f'</div>'
                )
            else:
                img_cell = '<span class="dim ns">no screenshot</span>'

            steps_html += (
                f'<tr class="sr s{st}">'
                f'<td class="cn2">{i+1}</td>'
                f'<td>{status_badge}</td>'
                f'<td class="ca">{parsed["action"]}</td>'
                f'<td class="ct">{parsed["target"]}</td>'
                f'<td>{conf_cell}</td>'
                f'<td>{img_cell}</td>'
                f'</tr>'
            )

        steps_passed = details.get("steps_passed", 0)
        steps_healed = details.get("steps_healed", 0)
        steps_total  = details.get("total_steps",  0)

        # Step summary string for card header
        if steps_healed > 0:
            step_summary = (
                f"{steps_passed}/{steps_total} steps · "
                f"{steps_healed} healed"
            )
        else:
            step_summary = f"{steps_passed}/{steps_total} steps"

        test_blocks += f"""
<div class="tc tc-{tc_class}" id="tc{idx}">
  <div class="tch" onclick="tog({idx})">
    <div class="tcl">
      <span class="dot d{tc_class}"></span>
      <span class="tn">{name}</span>
      <span class="tc-pill tcp-{tc_class}">{tc_icon} {tc_label}</span>
    </div>
    <div class="tcr">
      <span class="tm">{step_summary}</span>
      <span class="tconf" style="color:{conf_color};">{conf_pct}% confidence</span>
      <span class="chv" id="chv{idx}">&#9660;</span>
    </div>
  </div>
  <div class="tcb" id="tcb{idx}">
    <div class="tw2">
      <table class="st">
        <thead><tr><th>#</th><th>Status</th><th>Action</th>
        <th>Target / Description</th><th>Confidence</th>
        <th>Screenshot</th></tr></thead>
        <tbody>{steps_html}</tbody>
      </table>
    </div>
  </div>
</div>"""

    # ── Banner ────────────────────────────────────────────────────
    if failed_tests == 0 and passed_w_healing == 0:
        bclass = "bpass"
        btext  = (
            f"&#10003;  All {total_tests} test case(s) passed cleanly "
            f"&mdash; {passed_steps}/{total_steps} steps &middot; "
            f"{int(avg_conf*100)}% avg confidence"
        )
    elif failed_tests == 0 and passed_w_healing > 0:
        bclass = "bwarn"
        btext  = (
            f"&#9888;  {truly_passed} clean / "
            f"{passed_w_healing} passed with self-healing &mdash; "
            f"{passed_steps}/{total_steps} steps &middot; "
            f"{int(avg_conf*100)}% avg confidence"
        )
    else:
        bclass = "bfail"
        btext  = (
            f"&#10007;  {failed_tests}/{total_tests} test case(s) failed "
            f"&mdash; {passed_steps}/{total_steps} steps passed &middot; "
            f"{int(avg_conf*100)}% avg confidence"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Test Report — {run_time}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;800&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0c0e14;--bg2:#12151f;--bg3:#181c28;--bd:#232838;
  --tx:#dde3f0;--dm:#5a6280;--ac:#6366f1;
  --pa:#22d99a;--fa:#f87171;--wa:#fbbf24;--ha:#a78bfa;
  --mono:'JetBrains Mono',monospace;--head:'Syne',sans-serif;
}}
body{{background:var(--bg);color:var(--tx);font-family:var(--mono);font-size:12.5px;line-height:1.65;min-height:100vh}}

/* HEADER */
.ph{{background:linear-gradient(160deg,#0c0e14 0%,#12151f 60%,#181230 100%);border-bottom:1px solid var(--bd);padding:44px 52px 36px;position:relative;overflow:hidden}}
.ph::before{{content:'';position:absolute;top:-80px;right:-80px;width:360px;height:360px;background:radial-gradient(circle,rgba(99,102,241,.18) 0%,transparent 65%);pointer-events:none}}
.ey{{font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:var(--ac);margin-bottom:10px}}
.pt{{font-family:var(--head);font-size:30px;font-weight:800;color:#fff;letter-spacing:-.5px;margin-bottom:8px}}
.pt em{{font-style:normal;color:var(--ac)}}
.ps{{color:var(--dm);font-size:11.5px}}

/* STATS */
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:14px;padding:32px 52px}}
.sc{{background:var(--bg2);border:1px solid var(--bd);border-radius:14px;padding:22px 22px 18px;position:relative;overflow:hidden;transition:transform .18s,border-color .18s,box-shadow .18s;cursor:default}}
.sc:hover{{transform:translateY(-3px);border-color:var(--ac);box-shadow:0 8px 32px rgba(99,102,241,.12)}}
.sc::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;border-radius:0 0 14px 14px;opacity:.85}}
.s0::after{{background:var(--ac)}}.s1::after{{background:var(--pa)}}
.s2::after{{background:var(--fa)}}.s3::after{{background:var(--ha)}}
.s4::after{{background:var(--wa)}}.s5::after{{background:#38bdf8}}
.s6::after{{background:var(--wa)}}
.sl{{font-size:9.5px;letter-spacing:1.8px;text-transform:uppercase;color:var(--dm);margin-bottom:10px}}
.sv{{font-family:var(--head);font-size:38px;font-weight:800;line-height:1;margin-bottom:4px}}
.s0 .sv{{color:var(--ac)}}.s1 .sv{{color:var(--pa)}}.s2 .sv{{color:var(--fa)}}
.s3 .sv{{color:var(--ha)}}.s4 .sv{{color:var(--wa)}}.s5 .sv{{color:#38bdf8}}
.s6 .sv{{color:var(--wa)}}
.ss{{font-size:10.5px;color:var(--dm)}}

/* BANNER */
.bn{{margin:0 52px 28px;padding:15px 22px;border-radius:10px;font-family:var(--head);font-size:13.5px;font-weight:600}}
.bpass{{background:rgba(34,217,154,.07);border:1px solid rgba(34,217,154,.25);color:var(--pa)}}
.bwarn{{background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.3);color:var(--wa)}}
.bfail{{background:rgba(248,113,113,.07);border:1px solid rgba(248,113,113,.25);color:var(--fa)}}

/* SECTION */
.slb{{font-size:9.5px;letter-spacing:2.5px;text-transform:uppercase;color:var(--dm);font-weight:600;padding:0 52px 14px}}
.cards{{padding:0 52px 52px}}

/* TEST CARD */
.tc{{background:var(--bg2);border:1px solid var(--bd);border-radius:13px;margin-bottom:14px;overflow:hidden;transition:border-color .2s}}
.tc-pass{{border-left:3px solid var(--pa)}}
.tc-warn{{border-left:3px solid var(--wa)}}
.tc-fail{{border-left:3px solid var(--fa)}}
.tc:hover{{border-color:#2d3347}}
.tch{{display:flex;align-items:center;justify-content:space-between;padding:15px 20px;cursor:pointer;user-select:none;transition:background .15s}}
.tch:hover{{background:var(--bg3)}}
.tcl{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.tcr{{display:flex;align-items:center;gap:18px;font-size:11.5px;color:var(--dm)}}
.dot{{width:9px;height:9px;border-radius:50%;flex-shrink:0}}
.dpass{{background:var(--pa);box-shadow:0 0 7px var(--pa)}}
.dwarn{{background:var(--wa);box-shadow:0 0 7px var(--wa)}}
.dfail{{background:var(--fa);box-shadow:0 0 7px var(--fa)}}
.tn{{font-family:var(--head);font-size:13.5px;font-weight:600;color:var(--tx)}}

/* Status pill on test header */
.tc-pill{{font-family:var(--head);font-size:10px;font-weight:700;letter-spacing:.6px;padding:3px 10px;border-radius:20px;white-space:nowrap}}
.tcp-pass{{background:rgba(34,217,154,.12);color:var(--pa);border:1px solid rgba(34,217,154,.32)}}
.tcp-warn{{background:rgba(251,191,36,.12);color:var(--wa);border:1px solid rgba(251,191,36,.32)}}
.tcp-fail{{background:rgba(248,113,113,.12);color:var(--fa);border:1px solid rgba(248,113,113,.32)}}

.tconf{{font-weight:600;font-family:var(--head)}}
.chv{{font-size:10px;color:var(--dm);transition:transform .2s}}
.chv.open{{transform:rotate(180deg)}}
.tcb{{display:none;border-top:1px solid var(--bd)}}
.tcb.open{{display:block}}
.tw2{{overflow-x:auto}}

/* TABLE */
.st{{width:100%;border-collapse:collapse;font-size:12px}}
.st thead tr{{background:var(--bg3);border-bottom:1px solid var(--bd)}}
.st th{{padding:10px 16px;text-align:left;font-size:9.5px;letter-spacing:1.5px;text-transform:uppercase;color:var(--dm);font-weight:600;white-space:nowrap}}
.st td{{padding:11px 16px;border-bottom:1px solid rgba(35,40,56,.7);vertical-align:middle}}
.st tr:last-child td{{border-bottom:none}}
.st tr:hover td{{background:rgba(255,255,255,.018)}}
.spass td{{background:rgba(34,217,154,.02)}}
.sfail td{{background:rgba(248,113,113,.04)}}
.shealed td{{background:rgba(167,139,250,.04)}}
.swarn td{{background:rgba(251,191,36,.025)}}
.cn2{{color:var(--dm);min-width:28px;font-size:11px}}
.ca{{color:var(--ac);font-weight:600;min-width:70px}}
.ct{{color:var(--tx);max-width:280px;word-break:break-word}}

/* BADGES */
.badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:10px;font-weight:600;letter-spacing:.3px;white-space:nowrap}}
.bp{{background:rgba(34,217,154,.1);color:var(--pa);border:1px solid rgba(34,217,154,.28)}}
.bf{{background:rgba(248,113,113,.1);color:var(--fa);border:1px solid rgba(248,113,113,.28)}}
.bw{{background:rgba(251,191,36,.1);color:var(--wa);border:1px solid rgba(251,191,36,.28)}}
.bh{{background:rgba(167,139,250,.1);color:var(--ha);border:1px solid rgba(167,139,250,.28)}}
.bu{{background:rgba(90,98,128,.1);color:var(--dm);border:1px solid rgba(90,98,128,.28)}}

/* CONF BAR */
.cw{{display:flex;align-items:center;gap:8px}}
.cb{{height:4px;border-radius:4px;min-width:4px;flex-shrink:0;max-width:80px}}
.cn{{color:var(--dm);font-size:11px;white-space:nowrap}}

/* SCREENSHOTS */
.tw{{display:flex;flex-direction:column;align-items:center;gap:4px}}
.th{{width:92px;height:56px;object-fit:cover;border-radius:6px;border:1px solid var(--bd);cursor:zoom-in;transition:transform .18s,border-color .18s,box-shadow .18s;display:block}}
.th:hover{{transform:scale(1.08);border-color:var(--ac);box-shadow:0 4px 16px rgba(99,102,241,.25)}}
.tl{{font-size:9px;color:var(--dm);letter-spacing:.5px}}
.ns{{font-size:10px;font-style:italic}}
.dim{{color:var(--dm)}}

/* LIGHTBOX */
.lb{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.88);z-index:9999;align-items:center;justify-content:center;backdrop-filter:blur(6px)}}
.lb.open{{display:flex}}
.lb img{{max-width:92vw;max-height:88vh;border-radius:10px;border:1px solid var(--bd);box-shadow:0 30px 80px rgba(0,0,0,.85);animation:zi .18s ease}}
@keyframes zi{{from{{opacity:0;transform:scale(.92)}}to{{opacity:1;transform:scale(1)}}}}
.lbc{{position:fixed;top:18px;right:26px;font-size:26px;color:var(--dm);cursor:pointer;background:none;border:none;font-family:var(--mono);transition:color .2s;z-index:10000}}
.lbc:hover{{color:var(--tx)}}
.lbh{{position:fixed;bottom:22px;color:var(--dm);font-size:11px;letter-spacing:.5px}}

/* FOOTER */
.pf{{text-align:center;padding:22px 52px 40px;color:var(--dm);font-size:11px;letter-spacing:.5px;border-top:1px solid var(--bd)}}
.pf em{{font-style:normal;color:var(--ac)}}
</style>
</head>
<body>

<!-- Lightbox -->
<div class="lb" id="lb" onclick="closeLB()">
  <button class="lbc" onclick="closeLB()">&#10005;</button>
  <img id="lbI" src="" alt="Screenshot"/>
  <span class="lbh">Click anywhere or press Esc to close</span>
</div>

<!-- Header -->
<div class="ph">
  <div class="ey">Automated Test Execution &middot; Strict Mode</div>
  <div class="pt">&#128640; <em>GenAI</em> Test Report</div>
  <div class="ps">Generated {run_time} &nbsp;&middot;&nbsp; GPT-4o-mini + Selenium WebDriver &nbsp;&middot;&nbsp; Masters Project</div>
</div>

<!-- Stats -->
<div class="stats">
  <div class="sc s0">
    <div class="sl">Total Tests</div>
    <div class="sv">{total_tests}</div>
    <div class="ss">test cases</div>
  </div>
  <div class="sc s1">
    <div class="sl">Clean Pass</div>
    <div class="sv">{truly_passed}</div>
    <div class="ss">no healing required</div>
  </div>
  <div class="sc s6">
    <div class="sl">Passed (Healed)</div>
    <div class="sv">{passed_w_healing}</div>
    <div class="ss">recovered via healing</div>
  </div>
  <div class="sc s2">
    <div class="sl">Failed</div>
    <div class="sv">{failed_tests}</div>
    <div class="ss">tests failing</div>
  </div>
  <div class="sc s3">
    <div class="sl">Self-Healed Steps</div>
    <div class="sv">{healed_steps}</div>
    <div class="ss">total steps recovered</div>
  </div>
  <div class="sc s4">
    <div class="sl">Avg Confidence</div>
    <div class="sv">{int(avg_conf*100)}%</div>
    <div class="ss">all steps</div>
  </div>
  <div class="sc s5">
    <div class="sl">Steps</div>
    <div class="sv">{passed_steps}/{total_steps}</div>
    <div class="ss">steps passed</div>
  </div>
</div>

<!-- Banner -->
<div class="bn {bclass}">{btext}</div>

<!-- Test cases -->
<div class="slb">Test Case Details</div>
<div class="cards">{test_blocks}</div>

<!-- Footer -->
<div class="pf">GenAI Test Automation Framework &nbsp;&middot;&nbsp; Built with <em>GPT-4o-mini</em> + Selenium + Python &nbsp;&middot;&nbsp; Masters Project &nbsp;&middot;&nbsp; <em>Strict-Mode Pass Criteria</em></div>

<script>
window.addEventListener('DOMContentLoaded',function(){{tog(0);}});
function tog(i){{
  var b=document.getElementById('tcb'+i);
  var c=document.getElementById('chv'+i);
  if(!b)return;
  var o=b.classList.contains('open');
  b.classList.toggle('open',!o);
  c.classList.toggle('open',!o);
}}
function openModal(src){{
  document.getElementById('lbI').src=src;
  document.getElementById('lb').classList.add('open');
}}
function closeLB(){{document.getElementById('lb').classList.remove('open');}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeLB();}});
</script>
</body>
</html>"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"📄 Report generated: {report_path}")
    return report_path