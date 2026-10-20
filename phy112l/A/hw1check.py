"""hw1check: checker for PHY 112L HW 1 (Compressing a 2-D Ideal Gas).

Put this file in the same folder as your notebook (if you work on a cloud
server, upload it next to your notebook there).  Do not modify it.

In your notebook:

    # Setup
    import numpy as np
    import matplotlib.pyplot as plt
    import hw1check

    hw1check.report("P2 T", T)     # report each result once
    hw1check.figure("P2")          # right after making a plot, instead of plt.show()

    import hw1check; hw1check.run()    # in the last cell

Then use Kernel -> Restart & Run All, and check that the last cell says
"ready to submit".
"""

from __future__ import print_function

import base64
import io
import math
import re
import signal
import sys

import numpy as np

VERSION = "1.0"

# Results to report, in problem order.  Scalars unless listed in ARRAYS.
RESULTS = ["P2 T", "P3 T", "P4 T", "P5 O", "P6 A", "P6 O", "P6 W"]
ARRAYS = ["P6 A", "P6 O"]
FIGURES = ["P2", "P3", "P4", "P6"]

# Test values from the assignment, Problem 1: (ax, ay, bx, by, theta) -> expected.
_TAU = 2 * np.pi
COLLIDE_TESTS = [
    ((1, 0, -1, 0, 0), (1, 0, -1, 0)),
    ((1, 0, -1, 0, _TAU / 4), (0, 1, 0, -1)),
    ((1, 0, -1, 0, _TAU / 2), (-1, 0, 1, 0)),
    ((1, 0, -1, 0, 3 * _TAU / 4), (0, -1, 0, 1)),
    ((0, 1, 0, -1, 0), (0, 1, 0, -1)),
    ((0, 1, 0, -1, _TAU / 4), (-1, 0, 1, 0)),
    ((0, 1, 0, -1, _TAU / 2), (0, -1, 0, 1)),
    ((0, 1, 0, -1, 3 * _TAU / 4), (1, 0, -1, 0)),
    ((1, 1, 1, -1, 0), (1, 1, 1, -1)),
    ((1, 1, 1, -1, _TAU / 4), (0, 0, 2, 0)),
    ((1, 1, 1, -1, _TAU / 2), (1, -1, 1, 1)),
    ((1, 1, 1, -1, 3 * _TAU / 4), (2, 0, 0, 0)),
    ((6.24, 1.78, 3.35, 5.98, 3.19), (3.25, 5.91, 6.34, 1.85)),
    ((4.07, 4.69, 1.61, 4.54, 2.46), (1.84, 5.33, 3.84, 3.90)),
    ((5.28, 2.99, 4.77, 5.22, 3.15), (4.76, 5.22, 5.29, 2.99)),
    ((2.84, 5.37, 5.47, 6.16, 1.59), (4.58, 4.46, 3.73, 7.07)),
]
COLLIDE_TOL = 0.006  # expected values are rounded to 2 decimals

# Test value from the assignment, "The move function".
MOVE_TEST = (([1.0], [1.0], 4, 0, 10), ([3.0], [1.0], 2.0))

TIME_LIMIT = 20  # seconds per function test

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
    """Show a raw output bundle with hw1check metadata (prints text outside Jupyter)."""
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


# ---------------------------------------------------------------- student API

def report(name, value):
    """Report a result, e.g. hw1check.report("P2 T", T).  Call once per result."""
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
        print("hw1check: could not use the value reported as %r (%s)" % (name, e))
        _log.append(("bad", name, repr(value)[:200], _exec_count()))
        return
    if name not in RESULTS:
        print("hw1check: %r is not one of the results to report: %s"
              % (name, ", ".join(RESULTS)))
    print("RESULT %s = %s" % (name, _fmt_value(v)))
    _log.append(("result", name, v, _exec_count()))


def figure(name):
    """Register the current plot, e.g. hw1check.figure("P2").  Use instead of plt.show()."""
    import matplotlib.pyplot as plt
    name = str(name)
    fig = plt.gcf()
    empty = len(fig.get_axes()) == 0
    if name not in FIGURES:
        print("hw1check: %r is not one of the required plots: %s"
              % (name, ", ".join(FIGURES)))
    if empty:
        print("hw1check: plot %r is empty.  Call hw1check.figure right after making the plot, "
              "instead of plt.show()." % name)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    png = base64.b64encode(buf.getvalue()).decode("ascii")
    _display({"image/png": png, "text/plain": "<hw1check figure %s>" % name},
             {"hw1check": {"figure": name}},
             "hw1check: figure %s registered (not displayed outside Jupyter)" % name)
    _log.append(("figure", name, empty, _exec_count()))


# ---------------------------------------------------------------- checks

def _namespace():
    ip = _ipython()
    if ip is not None:
        return ip.user_ns
    return vars(sys.modules["__main__"])


def _check_collide(ns, todo):
    f = ns.get("collide")
    if not callable(f):
        todo.append("Define the function collide(ax, ay, bx, by, theta) (Problem 1).")
        return {"present": False}
    failed = []
    for args, expected in COLLIDE_TESTS:
        try:
            got = np.asarray(_call_with_limit(f, args), dtype=float).ravel()
            ok = got.shape == (4,) and np.all(np.abs(got - expected) <= COLLIDE_TOL)
            if not ok:
                failed.append("collide(%s) gave %s, expected %s"
                              % (_fmt_args(args), np.array2string(np.round(got, 2) + 0),
                                 list(expected)))
        except Exception as e:
            failed.append("collide(%s) %s" % (_fmt_args(args), _describe_error(e)))
            if isinstance(e, _Timeout):
                break
    passed = len(COLLIDE_TESTS) - len(failed)
    if failed:
        todo.append("collide fails %d of %d tests from Problem 1, e.g. %s"
                    % (len(failed), len(COLLIDE_TESTS), failed[0]))
    return {"present": True, "passed": passed, "total": len(COLLIDE_TESTS)}


def _check_temp(ns, todo):
    f = ns.get("temp")
    if not callable(f):
        todo.append("Define the function temp(vx, vy) as given in the text.")
        return {"present": False}
    try:
        got = float(_call_with_limit(f, (np.array([1.0, -1.0]), np.array([0.0, 2.0]))))
        ok = abs(got - 1.5) < 1e-9
    except Exception as e:
        todo.append("temp(vx, vy) %s" % _describe_error(e))
        return {"present": True, "passed": False}
    if not ok:
        todo.append("temp(vx, vy) does not match the definition in the text "
                    "(T = (<vx^2> + <vy^2>)/2).")
    return {"present": True, "passed": ok}


def _check_move(ns, todo):
    f = ns.get("move")
    if not callable(f):
        todo.append("Define the function move(y, vy, h, vp, dt) (see \"The move function\").")
        return {"present": False}
    (y, vy, h, vp, dt), (ey, evy, edvy) = MOVE_TEST
    try:
        out = _call_with_limit(f, (np.array(y), np.array(vy), h, vp, dt))
        if not isinstance(out, (tuple, list)) or len(out) != 3:
            todo.append("move(y, vy, h, vp, dt) must return three values: y, vy, dvy.")
            return {"present": True, "passed": False}
        gy, gvy, gdvy = out
        ok = (np.allclose(np.asarray(gy, dtype=float).ravel(), ey)
              and np.allclose(np.asarray(gvy, dtype=float).ravel(), evy)
              and np.isclose(float(np.sum(gdvy)), edvy))
    except Exception as e:
        todo.append("move test %s" % _describe_error(e))
        return {"present": True, "passed": False}
    if not ok:
        todo.append("move fails the test in \"The move function\": "
                    "move([1.], [1.], 4, 0, 10) gave y=%s, vy=%s, dvy=%s; expected [3.] [1.] 2.0"
                    % (np.asarray(gy).ravel()[:3], np.asarray(gvy).ravel()[:3], gdvy))
    return {"present": True, "passed": bool(ok)}


def _latest_results():
    latest, counts = {}, {}
    for kind, name, value, n in _log:
        if kind == "result":
            latest[name] = (value, n)
            counts[name] = counts.get(name, 0) + 1
    return latest, counts


def _judge(name, value, latest):
    """Return (verdict, hint) for one result; verdict is 'correct', 'off' or 'note'."""
    def get(other):
        return latest[other][0] if other in latest else None

    if name == "P2 T":
        return ("correct", "") if abs(value - 3.0) <= 0.1 else \
            ("off", "Problem 2: check your initialization and temp().")
    if name == "P3 T":
        p2 = get("P2 T")
        if p2 is None:
            return "note", "report P2 T to compare"
        return ("correct", "") if abs(value - p2) <= 1e-6 * max(1.0, abs(p2)) else \
            ("off", "Problem 3: collisions conserve energy, so T should not change.")
    if name == "P4 T":
        return ("correct", "") if abs(value - 1.0) <= 0.05 else \
            ("off", "Problem 4: the gas should reach the reservoir temperature.")
    if name == "P5 O":
        t = get("P4 T")
        t = 1.0 if t is None else t
        expected = t / 4.0
        if abs(value - expected) <= 0.04 * expected:
            return "correct", ""
        hint = "Problem 5: compare with Equation (iglaw)."
        if expected * 0.8 < value < expected:
            hint += "  Slightly low: see the hint (bounce multiple times)."
        return "off", hint
    if name == "P6 W":
        if abs(value - math.log(2)) <= 0.05:
            return "correct", ""
        hint = "Problem 6: compare with Equation (wiso)."
        if value > math.log(2):
            hint += "  Too high: check that your gas stays at T = 1 (enough reservoir collisions after each step)."
        return "off", hint
    return "note", ""


def _check_results(todo, notes):
    latest, counts = _latest_results()
    table = {}
    for name in RESULTS:
        if name not in latest:
            todo.append("Report %s with hw1check.report(\"%s\", ...)." % (name, name))
            continue
        value, n = latest[name]
        if counts[name] > 1:
            todo.append("%s was reported %d times; report each result once, "
                        "then use Kernel -> Restart & Run All." % (name, counts[name]))
        if name in ARRAYS:
            verdict, hint = "note", ""
        else:
            verdict, hint = _judge(name, value, latest)
            if verdict == "off":
                todo.append("%s = %s is not within the expected precision. %s"
                            % (name, _fmt(value), hint))
        table[name] = {"value": value, "verdict": verdict, "count": counts[name],
                       "exec_count": n}
    if "P6 A" in latest and "P6 O" in latest:
        a, o = latest["P6 A"][0], latest["P6 O"][0]
        if len(a) != len(o):
            todo.append("P6 A and P6 O must have the same length (one value per step); "
                        "got %d and %d." % (len(a), len(o)))
        elif len(a) != 20:
            notes.append("P6 A and P6 O have %d values; Problem 6 has 20 steps." % len(a))
    bad = [name for kind, name, value, n in _log if kind == "bad"]
    for name in sorted(set(bad)):
        todo.append("The value reported as %r could not be used (see the message where you reported it)."
                    % name)
    # problem order of the cells that reported results
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
            todo.append("Register your Problem %s plot with hw1check.figure(\"%s\")." % (name[1:], name))
        elif len(registered[name]) > 1:
            todo.append("Plot %s was registered %d times; register each plot once, "
                        "then use Kernel -> Restart & Run All." % (name, len(registered[name])))
        elif registered[name][-1]:
            todo.append("Plot %s is empty: call hw1check.figure(\"%s\") right after making the plot, "
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
        if "hw1check.run" in s:
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
    """Check the notebook.  Call in the last cell: import hw1check; hw1check.run()"""
    ns = _namespace()
    todo, notes = [], []
    functions = {
        "collide": _check_collide(ns, todo),
        "temp": _check_temp(ns, todo),
        "move": _check_move(ns, todo),
    }
    results = _check_results(todo, notes)
    figures = _check_figures(todo)
    session = _check_session(todo, notes)
    ready = not todo

    lines = ["hw1check %s" % VERSION, "", "Functions:"]
    for fname, r in sorted(functions.items()):
        if not r["present"]:
            lines.append("  %-8s missing" % fname)
        elif "total" in r:
            lines.append("  %-8s %d of %d tests passed" % (fname, r["passed"], r["total"]))
        else:
            lines.append("  %-8s %s" % (fname, "test passed" if r["passed"] else "test FAILED"))
    lines.append("")
    lines.append("Results:")
    for name in RESULTS:
        if name not in results:
            lines.append("  %-5s missing" % name)
            continue
        r = results[name]
        mark = {"correct": "correct", "off": "NOT within expected precision", "note": ""}[r["verdict"]]
        value = r["value"]
        shown = ("%d values" % len(value)) if isinstance(value, list) else _fmt(value)
        lines.append("  %-5s = %-12s %s" % (name, shown, mark))
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
    _display({"text/plain": text}, {"hw1check": {"summary": summary}}, text)
