"""hw2check: checker for PHY 112L HW 2 (A 2-D Ideal-Gas Atmosphere).

Put this file in the same folder as your notebook (if you work on a cloud
server, upload it next to your notebook there).  Do not modify it.

In your notebook:

    # Setup
    import numpy as np
    import matplotlib.pyplot as plt
    import hw2check

    hw2check.report("P1 C", C)     # report each result once
    hw2check.figure("P1b")         # right after making a plot, instead of plt.show()

    import hw2check; hw2check.run()    # in the last cell

Then use Kernel -> Restart & Run All, and check that the last cell says
"ready to submit".
"""

from __future__ import print_function

import base64
import io
import re
import signal
import sys

import numpy as np

VERSION = "1.0"

# Results to report, in problem order.  Scalars unless listed in ARRAYS.
RESULTS = ["P1 T", "P1 Q", "P1 C", "P2 TA", "P2 TB", "P3 A", "P3 O", "P3 W", "P3 T",
           "P4 T", "P4 U", "P5 y", "P6 TA", "P6 TB"]
ARRAYS = ["P1 T", "P1 Q", "P3 A", "P3 O"]
ARRAY_LENGTHS = {"P1 T": 4, "P1 Q": 4, "P3 A": 80, "P3 O": 80}
FIGURES = ["P1a", "P1b", "P3", "P5"]

# Expected values; a result is correct within REL_TOL of them (5%, 7.5% in Problem 3), which covers the spread
# of correct solutions over random seeds and reasonable method choices (tolerance_study.py).
REL_TOL = 0.05
REL_TOL_BY_NAME = {"P3 W": 0.075, "P3 T": 0.075}   # Problem 3 doubles the offset of the starting temperature
EXPECTED = {"P1 T": [2.0, 3.0, 4.0, 5.0], "P1 C": 1.0, "P2 TA": 1.5, "P2 TB": 1.5, "P3 W": 1.0,
            "P3 T": 2.0, "P4 T": 1.0, "P4 U": 2.0, "P5 y": 1.0, "P6 TA": 2.0, "P6 TB": 2.0}
Q_TOL = 0.02   # P1: the heat must equal the energy the gas gains, Q[i] - Q[0] = T[i] - T[0] (exactly, up to this)

# Test values from HW 1 (collide) and from this assignment (move_gravity).
COLLIDE_TESTS = [
    ((6.24, 1.78, 3.35, 5.98, 3.19), (3.25, 5.91, 6.34, 1.85)),
    ((4.07, 4.69, 1.61, 4.54, 2.46), (1.84, 5.33, 3.84, 3.90)),
    ((5.28, 2.99, 4.77, 5.22, 3.15), (4.76, 5.22, 5.29, 2.99)),
    ((2.84, 5.37, 5.47, 6.16, 1.59), (4.58, 4.46, 3.73, 7.07)),
]
COLLIDE_TOL = 0.006  # expected values are rounded to 2 decimals
MOVE_TEST = (([1.0], [1.0], 4, 0, 10), ([3.0], [1.0], 2.0))
MOVE_GRAVITY_TESTS = [(([1.0], [0.0], 1, 2), (0.657, 0.828)),
                      (([1.0], [0.0], 1, 5), (0.784, 0.657))]
MOVE_GRAVITY_TOL = 0.0006   # expected values are rounded to 3 decimals

N_TEST = 10000       # the gas size of the assignment, for the reservoir and gas-gas tests
TIME_LIMIT = 30      # seconds per function test

CELL_LABEL = re.compile(r"^#\s*(Setup|Problem\s+[1-6])\b")

# What was reported, in call order: (kind, name, value, execution count)
_log = []


# ---------------------------------------------------------------- helpers

def _ipython():
    try:
        return get_ipython()  # noqa: F821 (defined inside IPython/Jupyter)
    except NameError:
        return None


def _exec_count():
    ip = _ipython()
    if ip is None:
        return None
    try:
        return int(ip.execution_count)
    except Exception:
        return None


def _display(data, metadata, text):
    """Show a raw output bundle with hw2check metadata (prints text outside Jupyter)."""
    try:
        from IPython.display import display
    except ImportError:
        print(text)
        return
    if _ipython() is None:
        print(text)
        return
    display(data, raw=True, metadata=metadata)


def _fmt(x):
    return "%.6g" % x


def _fmt_args(args):
    return ", ".join("%.4g" % a for a in args)


def _fmt_value(value):
    if isinstance(value, list):
        return "[" + ", ".join(_fmt(v) for v in value) + "]"
    return _fmt(value)


class _Timeout(Exception):
    pass


def _call_with_limit(func, args):
    """Call func(*args), giving up after TIME_LIMIT seconds where the OS allows it."""
    use_alarm = hasattr(signal, "SIGALRM")
    if use_alarm:
        def _handler(signum, frame):
            raise _Timeout()
        try:
            old = signal.signal(signal.SIGALRM, _handler)
            signal.alarm(TIME_LIMIT)
        except ValueError:  # not in the main thread
            use_alarm = False
    try:
        return func(*args)
    finally:
        if use_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)


def _describe_error(e):
    if isinstance(e, _Timeout):
        return "did not finish within %d seconds (endless loop?)" % TIME_LIMIT
    return "raised %s: %s" % (type(e).__name__, e)


def _arrays(out, n, what):
    """out as n float arrays, or raise ValueError naming what was expected."""
    if not isinstance(out, (tuple, list)) or len(out) != n:
        raise ValueError("must return %d values: %s" % (n, what))
    return [np.asarray(x, dtype=float).ravel() for x in out]


def _energy(vx, vy):
    return 0.5 * np.sum(np.asarray(vx) ** 2 + np.asarray(vy) ** 2)


# ---------------------------------------------------------------- student API

def report(name, value):
    """Report a result, e.g. hw2check.report("P1 C", C).  Call once per result."""
    name = str(name)
    try:
        if name in ARRAYS:
            v = [float(x) for x in np.asarray(value, dtype=float).ravel()]
        else:
            v = float(np.asarray(value, dtype=float).reshape(-1)[0]) \
                if np.size(value) == 1 else None
            if v is None:
                raise ValueError("expected a single number, got %d values" % np.size(value))
    except Exception as e:
        print("hw2check: could not use the value reported as %r (%s)" % (name, e))
        _log.append(("bad", name, repr(value)[:200], _exec_count()))
        return
    if name not in RESULTS:
        print("hw2check: %r is not one of the results to report: %s"
              % (name, ", ".join(RESULTS)))
    print("RESULT %s = %s" % (name, _fmt_value(v)))
    _log.append(("result", name, v, _exec_count()))


def figure(name):
    """Register the current plot, e.g. hw2check.figure("P1b").  Use instead of plt.show()."""
    import matplotlib.pyplot as plt
    name = str(name)
    fig = plt.gcf()
    empty = len(fig.get_axes()) == 0
    if name not in FIGURES:
        print("hw2check: %r is not one of the required plots: %s"
              % (name, ", ".join(FIGURES)))
    if empty:
        print("hw2check: plot %r is empty.  Call hw2check.figure right after making the plot, "
              "instead of plt.show()." % name)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    png = base64.b64encode(buf.getvalue()).decode("ascii")
    _display({"image/png": png, "text/plain": "<hw2check figure %s>" % name},
             {"hw2check": {"figure": name}},
             "hw2check: figure %s registered (not displayed outside Jupyter)" % name)
    _log.append(("figure", name, empty, _exec_count()))


# ---------------------------------------------------------------- function checks

def _missing(ns, fname, signature, todo):
    if callable(ns.get(fname)):
        return False
    todo.append("Define the function %s as given in the text (see \"Required Functions\")." % signature)
    return True


def _check_collide(ns, todo):
    if _missing(ns, "collide", "collide(ax, ay, bx, by, theta)", todo):
        return {"present": False}
    f = ns["collide"]
    failed = []
    for args, expected in COLLIDE_TESTS:
        try:
            got = np.asarray(_call_with_limit(f, args), dtype=float).ravel()
            if not (got.shape == (4,) and np.all(np.abs(got - expected) <= COLLIDE_TOL)):
                failed.append("collide(%s) gave %s, expected %s"
                              % (_fmt_args(args), np.array2string(np.round(got, 2) + 0), list(expected)))
        except Exception as e:
            failed.append("collide(%s) %s" % (_fmt_args(args), _describe_error(e)))
            if isinstance(e, _Timeout):
                break
    if failed:
        todo.append("collide fails %d of %d tests from HW 1, e.g. %s"
                    % (len(failed), len(COLLIDE_TESTS), failed[0]))
    return {"present": True, "passed": len(COLLIDE_TESTS) - len(failed), "total": len(COLLIDE_TESTS)}


def _check_temp(ns, todo):
    if _missing(ns, "temp", "temp(vx, vy)", todo):
        return {"present": False}
    try:
        got = float(_call_with_limit(ns["temp"], (np.array([1.0, -1.0]), np.array([0.0, 2.0]))))
        ok = abs(got - 1.5) < 1e-9
    except Exception as e:
        todo.append("temp(vx, vy) %s" % _describe_error(e))
        return {"present": True, "passed": False}
    if not ok:
        todo.append("temp(vx, vy) does not match the definition (T = (<vx^2> + <vy^2>)/2).")
    return {"present": True, "passed": ok}


def _check_move(ns, todo):
    if _missing(ns, "move", "move(y, vy, h, vp, dt)", todo):
        return {"present": False}
    (y, vy, h, vp, dt), (ey, evy, edvy) = MOVE_TEST
    try:
        out = _call_with_limit(ns["move"], (np.array(y), np.array(vy), h, vp, dt))
        if not isinstance(out, (tuple, list)) or len(out) != 3:
            todo.append("move(y, vy, h, vp, dt) must return three values: y, vy, dvy.")
            return {"present": True, "passed": False}
        ok = (np.allclose(np.asarray(out[0], dtype=float).ravel(), ey)
              and np.allclose(np.asarray(out[1], dtype=float).ravel(), evy)
              and np.isclose(float(np.sum(out[2])), edvy))
    except Exception as e:
        todo.append("move test %s" % _describe_error(e))
        return {"present": True, "passed": False}
    if not ok:
        todo.append("move fails the HW 1 test: move([1.], [1.], 4, 0, 10) should give [3.] [1.] 2.0.")
    return {"present": True, "passed": bool(ok)}


def _check_collide_reservoir(ns, todo):
    if _missing(ns, "collide_reservoir", "collide_reservoir(vx, vy, Tr, ncoll)", todo):
        return {"present": False}
    rng = np.random.RandomState(2)
    vx, vy = rng.normal(0, 1, N_TEST), rng.normal(0, 1, N_TEST)
    e0, t0 = _energy(vx, vy) / N_TEST, 0.5 * (np.mean(vx ** 2) + np.mean(vy ** 2))
    try:
        gvx, gvy, gq = _arrays(_call_with_limit(ns["collide_reservoir"], (vx.copy(), vy.copy(), 2.0, 2 * N_TEST)),
                               3, "vx, vy, Q")
    except Exception as e:
        todo.append("collide_reservoir(vx, vy, 2, 20000) %s" % _describe_error(e))
        return {"present": True, "passed": False}
    problems = []
    if gvx.shape != (N_TEST,) or gvy.shape != (N_TEST,):
        problems.append("it should return the updated arrays vx and vy (same length as the input)")
    else:
        gained = _energy(gvx, gvy) / N_TEST - e0
        t1 = 0.5 * (np.mean(gvx ** 2) + np.mean(gvy ** 2))
        q = float(np.sum(gq))
        if not abs(q - gained) <= 1e-6 * max(1.0, abs(gained)):
            problems.append("Q = %.4g should equal the energy the gas gained, %.4g (in units of U_0: "
                            "a sum of (vx^2 + vy^2)/2 over the reservoir particles, divided by N)" % (q, gained))
        if not t0 < t1 < 2.0 + 0.1:
            problems.append("a gas at T = %.3g in contact with a reservoir at T = 2 ended at T = %.3g" % (t0, t1))
    if problems:
        todo.append("collide_reservoir test (a gas of %d molecules at T = 1, reservoir at 2, 20000 collisions): %s."
                    % (N_TEST, "; ".join(problems)))
    return {"present": True, "passed": not problems}


def _check_collide_gases(ns, todo):
    if _missing(ns, "collide_gases", "collide_gases(vxa, vya, vxb, vyb, ncoll)", todo):
        return {"present": False}
    rng = np.random.RandomState(3)
    va = [rng.normal(0, 1, N_TEST), rng.normal(0, 1, N_TEST)]
    vb = [rng.normal(0, np.sqrt(3), N_TEST), rng.normal(0, np.sqrt(3), N_TEST)]
    e0 = _energy(*va) + _energy(*vb)
    ta0, tb0 = [0.5 * (np.mean(v[0] ** 2) + np.mean(v[1] ** 2)) for v in (va, vb)]
    try:
        out = _arrays(_call_with_limit(ns["collide_gases"], (va[0].copy(), va[1].copy(), vb[0].copy(),
                                                             vb[1].copy(), 2 * N_TEST)), 4, "vxa, vya, vxb, vyb")
    except Exception as e:
        todo.append("collide_gases(vxa, vya, vxb, vyb, 20000) %s" % _describe_error(e))
        return {"present": True, "passed": False}
    problems = []
    if any(x.shape != (N_TEST,) for x in out):
        problems.append("it should return the four updated arrays (same lengths as the input)")
    else:
        e1 = _energy(out[0], out[1]) + _energy(out[2], out[3])
        ta1, tb1 = 0.5 * (np.mean(out[0] ** 2) + np.mean(out[1] ** 2)), 0.5 * (np.mean(out[2] ** 2) + np.mean(out[3] ** 2))
        if not abs(e1 - e0) <= 1e-6 * e0:
            problems.append("the total energy of the two gases changed by %.2g%% (collisions conserve it)"
                            % (100 * (e1 - e0) / e0))
        if not (ta0 < ta1 and tb1 < tb0):
            problems.append("gas A at T = %.3g and gas B at T = %.3g ended at %.3g and %.3g: "
                            "heat should flow from B to A" % (ta0, tb0, ta1, tb1))
    if problems:
        todo.append("collide_gases test (gas A at T = 1, gas B at T = 3, 20000 collisions): %s." % "; ".join(problems))
    return {"present": True, "passed": not problems}


def _check_move_gravity(ns, todo):
    if _missing(ns, "move_gravity", "move_gravity(y, vy, g, dt)", todo):
        return {"present": False}
    failed = []
    for (y, vy, g, dt), (ey, evy) in MOVE_GRAVITY_TESTS:
        try:
            gy, gvy = _arrays(_call_with_limit(ns["move_gravity"], (np.array(y), np.array(vy), g, dt)), 2, "y, vy")
            if not (gy.shape == (1,) and gvy.shape == (1,) and abs(gy[0] - ey) <= MOVE_GRAVITY_TOL
                    and abs(gvy[0] - evy) <= MOVE_GRAVITY_TOL):
                failed.append("move_gravity([1.], [0.], 1, %g) gave y = %s, vy = %s; expected %.3f, %.3f"
                              % (dt, np.round(gy, 3), np.round(gvy, 3), ey, evy))
        except Exception as e:
            failed.append("move_gravity([1.], [0.], 1, %g) %s" % (dt, _describe_error(e)))
            if isinstance(e, _Timeout):
                break
    if failed:
        todo.append("move_gravity fails %d of %d tests from \"Required Functions\", e.g. %s"
                    % (len(failed), len(MOVE_GRAVITY_TESTS), failed[0]))
    return {"present": True, "passed": len(MOVE_GRAVITY_TESTS) - len(failed), "total": len(MOVE_GRAVITY_TESTS)}


# ---------------------------------------------------------------- results

def _latest_results():
    latest, counts = {}, {}
    for kind, name, value, n in _log:
        if kind == "result":
            latest[name] = (value, n)
            counts[name] = counts.get(name, 0) + 1
    return latest, counts


def _close(value, expected, name=None):
    return abs(value - expected) <= REL_TOL_BY_NAME.get(name, REL_TOL) * abs(expected)


HINTS = {
    "P1 C": "Problem 1: the slope of the total heat versus temperature; compare with Equation (cv) for f = 2.",
    "P2 TA": "Problem 2: equal heat capacities, so both gases should reach the average temperature.",
    "P2 TB": "Problem 2: equal heat capacities, so both gases should reach the average temperature.",
    "P3 T": "Problem 3: compressing from 4a to 2a should double the temperature (Equation (tadi)).",
    "P4 T": "Problem 4: the gas should reach the reservoir temperature.",
    "P4 U": "Problem 4: U/U_0 = T/T_0 + <y/a>: include the gravitational potential energy.",
    "P5 y": "Problem 5: compare with Equation (expy); check that gravity is on (g = 1) in Problem 4.",
    "P6 TA": "Problem 6: compare with Equation (tcontact), C_A = 2 and C_B = 1.  Gravity on gas A only.",
    "P6 TB": "Problem 6: compare with Equation (tcontact), C_A = 2 and C_B = 1.  Gravity on gas A only.",
}


def _judge(name, value, latest):
    """Return (verdict, hint) for one result; verdict is 'correct', 'off' or 'note'."""
    if name in ("P3 A", "P3 O"):
        return "note", ""
    if name == "P1 T":
        exp = EXPECTED[name]
        if len(value) == len(exp) and all(_close(v, e) for v, e in zip(value, exp)):
            return "correct", ""
        return "off", "Problem 1: after each 10 N collisions the gas should be at the reservoir temperature, 2 to 5."
    if name == "P1 Q":
        t = latest.get("P1 T", (None,))[0]
        if t is None or len(t) != len(value):
            return "note", "report P1 T (same length) to compare"
        if len(value) < 2:
            return "off", "Problem 1: four totals of heat, at the four temperature points."
        dq = [q - value[0] for q in value]
        dt = [x - t[0] for x in t]
        if all(abs(a - b) <= Q_TOL for a, b in zip(dq, dt)) and _close(value[0] + 1.0, t[0]):
            return "correct", ""
        ratio = (dq[-1] / dt[-1]) if dt[-1] else float("nan")
        return "off", ("Problem 1: the heat should equal the energy the gas gains, Q = Delta T in our units "
                       "(the steps of your Q are %.3g times those of T).  Check the units of Q in collide_reservoir."
                       % ratio)
    if name == "P3 W":
        if _close(value, EXPECTED[name], name):
            return "correct", ""
        hint = "Problem 3: compare with Equation (wadi)."
        if value > EXPECTED[name]:
            hint += "  Too high: re-thermalize the gas after each step (N self-collisions)."
        return "off", hint
    if name in EXPECTED:
        if _close(value, EXPECTED[name], name):
            return "correct", ""
        return "off", HINTS.get(name, "")
    return "note", ""


def _check_results(todo, notes):
    latest, counts = _latest_results()
    table = {}
    for name in RESULTS:
        if name not in latest:
            todo.append("Report %s with hw2check.report(\"%s\", ...)." % (name, name))
            continue
        value, n = latest[name]
        if counts[name] > 1:
            todo.append("%s was reported %d times; report each result once, "
                        "then use Kernel -> Restart & Run All." % (name, counts[name]))
        if name in ARRAY_LENGTHS and len(value) != ARRAY_LENGTHS[name]:
            todo.append("%s should have %d values; got %d." % (name, ARRAY_LENGTHS[name], len(value)))
            verdict, hint = "off", ""
        else:
            verdict, hint = _judge(name, value, latest)
            if verdict == "off":
                shown = _fmt_value(value)
                todo.append("%s = %s is not within the expected precision. %s" % (name, shown, hint))
        table[name] = {"value": value, "verdict": verdict, "count": counts[name], "exec_count": n}
    if "P3 A" in latest and "P3 O" in latest:
        a, o = latest["P3 A"][0], latest["P3 O"][0]
        if len(a) == len(o) == 80:
            oa2 = np.mean(np.array(o) * np.array(a) ** 2) / 4.0
            if not abs(oa2 - 1) <= 0.1:
                notes.append("P3: O A^2 / (4 T_1) averages %.3g; Equation (oadi) gives 1." % oa2)
    bad = [name for kind, name, value, n in _log if kind == "bad"]
    for name in sorted(set(bad)):
        todo.append("The value reported as %r could not be used (see the message where you reported it)." % name)
    order = [latest[name][1] for name in RESULTS if name in latest]
    if None not in order and order != sorted(order):
        notes.append("Results were reported out of problem order; "
                     "keep your cells in order and use Kernel -> Restart & Run All.")
    return table


def _check_figures(todo):
    registered = {}
    for kind, name, empty, n in _log:
        if kind == "figure":
            registered.setdefault(name, []).append(empty)
    for name in FIGURES:
        if name not in registered:
            todo.append("Register your plot %s with hw2check.figure(\"%s\")." % (name, name))
        elif len(registered[name]) > 1:
            todo.append("Plot %s was registered %d times; register each plot once, "
                        "then use Kernel -> Restart & Run All." % (name, len(registered[name])))
        elif registered[name][-1]:
            todo.append("Plot %s is empty: call hw2check.figure(\"%s\") right after making the plot, "
                        "instead of plt.show()." % (name, name))
    return sorted(registered)


def _check_session(todo, notes):
    """Look for signs that the notebook was not run cleanly from top to bottom."""
    info = {}
    if getattr(sys, "last_traceback", None) is not None:
        todo.append("A cell raised an error in this session.  Fix it, "
                    "then use Kernel -> Restart & Run All.")
        info["error"] = True
    ip = _ipython()
    if ip is None:
        return info
    try:
        cells = [c for c in ip.history_manager.input_hist_raw[1:]]
    except Exception:
        return info
    info["cells_run"] = len(cells)
    seen, repeats, unlabeled = set(), 0, []
    for src in cells:
        s = src.strip()
        if not s:
            continue
        if s in seen:
            repeats += 1
        seen.add(s)
        if "hw2check.run" in s:
            continue
        first = s.splitlines()[0].strip()
        if not CELL_LABEL.match(first):
            unlabeled.append(first[:40])
    info["repeated_cells"] = repeats
    info["unlabeled_cells"] = len(unlabeled)
    if repeats:
        notes.append("%d cell(s) were run more than once in this session.  Before submitting, "
                     "use Kernel -> Restart & Run All." % repeats)
    if unlabeled:
        todo.append("%d code cell(s) do not start with \"# Setup\" or \"# Problem N\", e.g. %r."
                    % (len(unlabeled), unlabeled[0]))
    return info


def run():
    """Check the notebook.  Call in the last cell: import hw2check; hw2check.run()"""
    ns = _namespace()
    todo, notes = [], []
    functions = {
        "collide": _check_collide(ns, todo),
        "temp": _check_temp(ns, todo),
        "move": _check_move(ns, todo),
        "collide_reservoir": _check_collide_reservoir(ns, todo),
        "collide_gases": _check_collide_gases(ns, todo),
        "move_gravity": _check_move_gravity(ns, todo),
    }
    results = _check_results(todo, notes)
    figures = _check_figures(todo)
    session = _check_session(todo, notes)
    ready = not todo

    lines = ["hw2check %s" % VERSION, "", "Functions:"]
    for fname in ("collide", "temp", "move", "collide_reservoir", "collide_gases", "move_gravity"):
        r = functions[fname]
        if not r["present"]:
            lines.append("  %-18s missing" % fname)
        elif "total" in r:
            lines.append("  %-18s %d of %d tests passed" % (fname, r["passed"], r["total"]))
        else:
            lines.append("  %-18s %s" % (fname, "test passed" if r["passed"] else "test FAILED"))
    lines.append("")
    lines.append("Results:")
    for name in RESULTS:
        if name not in results:
            lines.append("  %-6s missing" % name)
            continue
        r = results[name]
        mark = {"correct": "correct", "off": "NOT within expected precision", "note": ""}[r["verdict"]]
        value = r["value"]
        shown = ("%d values" % len(value)) if isinstance(value, list) else _fmt(value)
        lines.append("  %-6s = %-12s %s" % (name, shown, mark))
    lines.append("")
    lines.append("Plots: " + (", ".join(figures) if figures else "none registered"))
    if notes:
        lines.append("")
        lines.append("Notes:")
        lines.extend("  - " + n for n in notes)
    lines.append("")
    if ready:
        lines.append("READY TO SUBMIT (if you used Kernel -> Restart & Run All).")
    else:
        lines.append("NOT READY. To do:")
        lines.extend("  - " + t for t in todo)
        lines.append("")
        lines.append("If you cannot fix these, explain why in a text (markdown) cell at the end "
                     "of your notebook, then submit.")
    text = "\n".join(lines)

    summary = {
        "version": VERSION,
        "ready": ready,
        "todo": todo,
        "notes": notes,
        "functions": functions,
        "results": results,
        "figures": figures,
        "session": session,
        "log": [[kind, name, value, n] for kind, name, value, n in _log],
    }
    _display({"text/plain": text}, {"hw2check": {"summary": summary}}, text)


def _namespace():
    ip = _ipython()
    if ip is not None:
        return ip.user_ns
    return vars(sys.modules["__main__"])
