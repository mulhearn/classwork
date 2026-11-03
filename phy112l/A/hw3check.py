"""hw3check: checker for PHY 112L HW 3 (Entropy of a 2-D Ideal-Gas).

Put this file in the same folder as your notebook (if you work on a cloud
server, upload it next to your notebook there).  Do not modify it.

In your notebook:

    # Setup
    import numpy as np
    import matplotlib.pyplot as plt
    import hw3check

    hw3check.report("P1 S", S)     # report each result once
    hw3check.figure("P3")          # right after making a plot, instead of plt.show()

    import hw3check; hw3check.run()    # in the last cell

Then use Kernel -> Restart & Run All, and check that the last cell says
"ready to submit".
"""

from __future__ import print_function

import base64
import inspect
import io
import re
import signal
import sys

import numpy as np

VERSION = "1.0"

# Results to report, in problem order.  All scalars.
RESULTS = ["P1 S", "P2 dS", "P2 T", "P3 dS", "P4 pup", "P4 T", "P5 dS"]
ARRAYS = []
ARRAY_LENGTHS = {}
FIGURES = ["P3", "P4"]

# Expected values; a result is correct within REL_TOL of them, which covers the spread of correct solutions over
# random seeds with the assignment's procedure (tolerance_study.py).
_ALPHA = np.exp(-1.0)                       # V_step = 1 V_0 at T = 1 T_0
_PUP, _PDN = _ALPHA / (1 + _ALPHA), 1 / (1 + _ALPHA)
REL_TOL = 0.05
REL_TOL_BY_NAME = {"P2 dS": 0.075}   # Problem 2: the velocity bins (width 0.5 v_0) bias Delta S about 3% low
EXPECTED = {"P1 S": float(np.log(20 * 20 * 4)), "P2 dS": float(np.log(2)), "P2 T": 2.0,
            "P3 dS": float(np.log(2)), "P4 pup": float(_PUP), "P4 T": 1.0,
            "P5 dS": float(-(_PUP * np.log(_PUP) + _PDN * np.log(_PDN)))}

# Test values from "Required Functions" (gibbs_entropy, bounce, reflect), and a few of our own.
GIBBS_TESTS = [  # (vx, vy, y), expected S, what it tests
    (([0.2, 0.2, -0.2, -0.2], [0.2, 0.2, 0.2, 0.2], [1.5, 1.5, 1.5, 3.5]), 1.5 * np.log(2),
     "the first test value in \"Required Functions\" (1.04)"),
    (([0.2, 0.2, -0.2, -0.2], [0.2, 0.2, 0.2, 0.2], [1.5, 1.5, 1.5, 1.5]), np.log(2),
     "the second test value in \"Required Functions\" (0.693)"),
    (([0.1, 0.4], [0.1, 0.4], [0.5, 0.9]), 0.0,
     "two molecules in the same cell (vx and vy in 0 to 0.5, y in 0 to 1) should give S = 0:  the bins must be "
     "set by vmax and by the container height 4a, not by the range of the data"),
]
GIBBS_ARGS = {"hbins": 4, "vmax": 5, "vbins": 20}
GIBBS_TOL = 1e-6
STEP_TEST = (([1.0, -1.0], [1.0, 0.05], 0.1), [1.1, -0.05])     # (vy, y, dt) -> y;  no walls in step
BOUNCE_TEST = (([-1.0, 2.0, 1.0], [-0.1, 4.3, 2.0], 4), ([0.1, 3.7, 2.0], [1.0, -2.0, 1.0]))
REFLECT_TEST = (([1.0, 2.0, -1.0, 1.0], [1.95, 1.9, 2.05, 1.0], [2.05, 2.1, 1.95, 1.1], 2, 1),
                ([1.95, 2.1, 1.95, 1.1], [-1.0, np.sqrt(2.0), -np.sqrt(3.0), 1.0]))
MOTION_TOL = 1e-6

# Required functions and their keyword-only arguments (HW 1, Section "Keyword-Only Arguments").
REQUIRED_PARAMS = {"temp": ["vx", "vy"], "collide_reservoir": ["vx", "vy", "Tr", "ncoll"],
                   "gibbs_entropy": ["vx", "vy", "y", "hbins", "vmax", "vbins"], "step": ["vy", "y", "dt"],
                   "bounce": ["vy", "y", "h"], "reflect": ["vy", "y_old", "y", "h_step", "V_step"]}
FUNCTIONS = ["temp", "collide_reservoir", "gibbs_entropy", "step", "bounce", "reflect"]

N_TEST = 10000       # the gas size of the assignment, for the reservoir test
TIME_LIMIT = 30      # seconds per function test

CELL_LABEL = re.compile(r"^#\s*(Setup|Problem\s+[1-5])\b")

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
    """Show a raw output bundle with hw3check metadata (prints text outside Jupyter)."""
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
    """Report a result, e.g. hw3check.report("P1 S", S).  Call once per result."""
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
        print("hw3check: could not use the value reported as %r (%s)" % (name, e))
        _log.append(("bad", name, repr(value)[:200], _exec_count()))
        return
    if name not in RESULTS:
        print("hw3check: %r is not one of the results to report: %s"
              % (name, ", ".join(RESULTS)))
    print("RESULT %s = %s" % (name, _fmt_value(v)))
    _log.append(("result", name, v, _exec_count()))


def figure(name):
    """Register the current plot, e.g. hw3check.figure("P3").  Use instead of plt.show()."""
    import matplotlib.pyplot as plt
    name = str(name)
    fig = plt.gcf()
    empty = len(fig.get_axes()) == 0
    if name not in FIGURES:
        print("hw3check: %r is not one of the required plots: %s"
              % (name, ", ".join(FIGURES)))
    if empty:
        print("hw3check: plot %r is empty.  Call hw3check.figure right after making the plot, "
              "instead of plt.show()." % name)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    png = base64.b64encode(buf.getvalue()).decode("ascii")
    _display({"image/png": png, "text/plain": "<hw3check figure %s>" % name},
             {"hw3check": {"figure": name}},
             "hw3check: figure %s registered (not displayed outside Jupyter)" % name)
    _log.append(("figure", name, empty, _exec_count()))


# ---------------------------------------------------------------- function checks

def _signature(fname):
    return "%s(*, %s)" % (fname, ", ".join(REQUIRED_PARAMS[fname]))


def _missing(ns, fname, todo):
    if callable(ns.get(fname)):
        return False
    todo.append("Define the function %s as given in the text (see \"Required Functions\")." % _signature(fname))
    return True


def _keyword_only(ns, fname, todo):
    """A caller that passes the required arguments by name, in the assignment's order, or None (with a to-do)
    if the function does not take exactly those keyword-only arguments."""
    f = ns[fname]
    names = REQUIRED_PARAMS[fname]
    try:
        params = inspect.signature(f).parameters
    except (TypeError, ValueError):
        params = {}
    kwonly = [n for n, p in params.items() if p.kind == inspect.Parameter.KEYWORD_ONLY]
    if all(n in kwonly for n in names):
        return lambda *values: f(**dict(zip(names, values)))
    if kwonly:
        todo.append("%s has keyword-only arguments, but not the required names:  define it as def %s."
                    % (fname, _signature(fname)))
    else:
        todo.append("%s takes positional arguments:  define it with keyword-only arguments, "
                    "def %s (HW 1, Section \"Keyword-Only Arguments\" and Appendix)." % (fname, _signature(fname)))
    return None


def _call_unchanged(f, args):
    """Call f on copies of args;  return (output, True if any array argument was changed)."""
    copies = [np.array(a, dtype=float) if isinstance(a, (list, np.ndarray)) else a for a in args]
    before = [c.copy() if isinstance(c, np.ndarray) else None for c in copies]
    out = _call_with_limit(f, copies)
    changed = any(b is not None and not np.array_equal(b, c) for b, c in zip(before, copies))
    return out, changed


def _in_place(fname, todo):
    todo.append("%s changed the arrays passed to it:  every required function returns its results instead "
                "(\"Required Functions\"), e.g. start with y = y.copy()." % fname)


def _check_temp(ns, todo):
    if _missing(ns, "temp", todo):
        return {"present": False}
    f = _keyword_only(ns, "temp", todo)
    if f is None:
        return {"present": True, "passed": False, "signature": "positional"}
    try:
        got = float(_call_with_limit(f, (np.array([1.0, -1.0]), np.array([0.0, 2.0]))))
        ok = abs(got - 1.5) < 1e-9
    except Exception as e:
        todo.append("temp(vx, vy) %s" % _describe_error(e))
        return {"present": True, "passed": False}
    if not ok:
        todo.append("temp(vx, vy) does not match the definition (T = (<vx^2> + <vy^2>)/2).")
    return {"present": True, "passed": ok, "signature": "keyword-only"}


def _check_collide_reservoir(ns, todo):
    if _missing(ns, "collide_reservoir", todo):
        return {"present": False}
    f = _keyword_only(ns, "collide_reservoir", todo)
    if f is None:
        return {"present": True, "passed": False, "signature": "positional"}
    rng = np.random.RandomState(2)
    vx, vy = rng.normal(0, 1, N_TEST), rng.normal(0, 1, N_TEST)
    e0, t0 = _energy(vx, vy) / N_TEST, 0.5 * (np.mean(vx ** 2) + np.mean(vy ** 2))
    try:
        out, changed = _call_unchanged(f, (vx, vy, 2.0, 2 * N_TEST))
        gvx, gvy, gq = _arrays(out, 3, "vx, vy, Q")
    except Exception as e:
        todo.append("collide_reservoir(vx=vx, vy=vy, Tr=2, ncoll=20000) %s" % _describe_error(e))
        return {"present": True, "passed": False}
    problems = []
    if gvx.shape != (N_TEST,) or gvy.shape != (N_TEST,):
        problems.append("it should return the updated arrays vx and vy (same length as the input)")
    else:
        gained = _energy(gvx, gvy) / N_TEST - e0
        t1 = 0.5 * (np.mean(gvx ** 2) + np.mean(gvy ** 2))
        q = float(np.sum(gq))
        if not abs(q - gained) <= 1e-6 * max(1.0, abs(gained)):
            problems.append("Q = %.4g should equal the energy the gas gained, %.4g (in units of U_0, as in HW 2)"
                            % (q, gained))
        if not t0 < t1 < 2.0 + 0.1:
            problems.append("a gas at T = %.3g in contact with a reservoir at T = 2 ended at T = %.3g" % (t0, t1))
    if problems:
        todo.append("collide_reservoir test (a gas of %d molecules at T = 1, reservoir at 2, 20000 collisions): %s."
                    % (N_TEST, "; ".join(problems)))
    if changed:
        _in_place("collide_reservoir", todo)
    return {"present": True, "passed": not problems and not changed, "signature": "keyword-only"}


def _check_gibbs_entropy(ns, todo):
    if _missing(ns, "gibbs_entropy", todo):
        return {"present": False}
    f = _keyword_only(ns, "gibbs_entropy", todo)
    if f is None:
        return {"present": True, "passed": 0, "total": len(GIBBS_TESTS), "signature": "positional"}
    failed, changed = [], False
    for (vx, vy, y), expected, what in GIBBS_TESTS:
        try:
            out, ch = _call_unchanged(f, (vx, vy, y, GIBBS_ARGS["hbins"], GIBBS_ARGS["vmax"], GIBBS_ARGS["vbins"]))
            changed = changed or ch
            got = np.asarray(out, dtype=float).ravel()
            if not (got.shape == (1,) and abs(got[0] - expected) <= GIBBS_TOL):
                failed.append("%s:  got %s, expected %.4g" % (what, np.round(got, 4), expected))
        except Exception as e:
            failed.append("%s:  %s" % (what, _describe_error(e)))
            if isinstance(e, _Timeout):
                break
    if failed:
        todo.append("gibbs_entropy (hbins=4, vmax=5, vbins=20) fails %d of %d tests, e.g. %s"
                    % (len(failed), len(GIBBS_TESTS), failed[0]))
    if changed:
        _in_place("gibbs_entropy", todo)
    return {"present": True, "passed": len(GIBBS_TESTS) - len(failed), "total": len(GIBBS_TESTS),
            "signature": "keyword-only"}


def _check_motion(ns, todo, fname, test, nout, what, call):
    """One test of step, bounce or reflect:  test = (args, expected arrays);  nout = number of returned arrays."""
    if _missing(ns, fname, todo):
        return {"present": False}
    f = _keyword_only(ns, fname, todo)
    if f is None:
        return {"present": True, "passed": False, "signature": "positional"}
    args, expected = test
    if nout == 1:
        expected = (expected,)
    try:
        out, changed = _call_unchanged(f, args)
        got = [np.asarray(out, dtype=float).ravel()] if nout == 1 else _arrays(out, nout, what)
        ok = all(g.shape == np.shape(e) and np.all(np.abs(g - e) <= MOTION_TOL) for g, e in zip(got, expected))
    except Exception as e:
        todo.append("%s %s" % (call, _describe_error(e)))
        return {"present": True, "passed": False}
    if not ok:
        todo.append("%s gave %s; expected %s." % (call, " ".join(np.array2string(np.round(g, 3) + 0) for g in got),
                                                  " ".join(np.array2string(np.round(np.array(e), 3) + 0)
                                                           for e in expected)))
    if changed:
        _in_place(fname, todo)
    return {"present": True, "passed": bool(ok) and not changed, "signature": "keyword-only"}


def _check_step(ns, todo):
    return _check_motion(ns, todo, "step", STEP_TEST, 1, "y",
                         "step(vy=[1., -1.], y=[1., 0.05], dt=0.1) (no walls in step:  bounce does them)")


def _check_bounce(ns, todo):
    return _check_motion(ns, todo, "bounce", BOUNCE_TEST, 2, "y, vy",
                         "bounce(vy=[-1., 2., 1.], y=[-0.1, 4.3, 2.], h=4) (the test in \"Required Functions\")")


def _check_reflect(ns, todo):
    return _check_motion(ns, todo, "reflect", REFLECT_TEST, 2, "y, vy",
                         "reflect(...) (the test in \"Required Functions\")")


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
    "P1 S": "Problem 1: a uniform sample should give about ln M = 7.38 for M = 20 x 20 x 4 cells;  check the bins "
            "(hbins=4, vmax=5, vbins=20) and the y range 0 to 4a.",
    "P2 dS": "Problem 2: heating at constant volume from T = 1 to 2 gives Delta S/(kN) = ln 2.  Keep the bins the same "
             "for both states, and sum the visits over the 50 snapshots.",
    "P2 T": "Problem 2: the gas should reach the reservoir temperature, T_R = 2.",
    "P3 dS": "Problem 3: doubling the volume at constant temperature gives Delta S/(kN) = ln 2.  Keep the y range "
             "0 to 4a for both states.",
    "P4 pup": "Problem 4: p_up = alpha/(1 + alpha), alpha = exp(-V_step/kT) = exp(-1) at T = 1:  0.269.",
    "P4 T": "Problem 4: the reservoir keeps the gas at T = 1.",
    "P5 dS": "Problem 5: Delta S/(kN) = -(p_up ln p_up + p_dn ln p_dn) = 0.582 at T = 1.",
}


def _judge(name, value, latest):
    """Return (verdict, hint) for one result; verdict is 'correct', 'off' or 'note'."""
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
            todo.append("Report %s with hw3check.report(\"%s\", ...)." % (name, name))
            continue
        value, n = latest[name]
        if counts[name] > 1:
            todo.append("%s was reported %d times; report each result once, "
                        "then use Kernel -> Restart & Run All." % (name, counts[name]))
        verdict, hint = _judge(name, value, latest)
        if verdict == "off":
            todo.append("%s = %s is not within the expected precision. %s" % (name, _fmt_value(value), hint))
        table[name] = {"value": value, "verdict": verdict, "count": counts[name], "exec_count": n}
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
            todo.append("Register your plot %s with hw3check.figure(\"%s\")." % (name, name))
        elif len(registered[name]) > 1:
            todo.append("Plot %s was registered %d times; register each plot once, "
                        "then use Kernel -> Restart & Run All." % (name, len(registered[name])))
        elif registered[name][-1]:
            todo.append("Plot %s is empty: call hw3check.figure(\"%s\") right after making the plot, "
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
        if "hw3check.run" in s:
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
    """Check the notebook.  Call in the last cell: import hw3check; hw3check.run()"""
    ns = _namespace()
    todo, notes = [], []
    checks = {"temp": _check_temp, "collide_reservoir": _check_collide_reservoir,
              "gibbs_entropy": _check_gibbs_entropy, "step": _check_step, "bounce": _check_bounce,
              "reflect": _check_reflect}
    functions = {fname: checks[fname](ns, todo) for fname in FUNCTIONS}
    results = _check_results(todo, notes)
    figures = _check_figures(todo)
    session = _check_session(todo, notes)
    ready = not todo

    lines = ["hw3check %s" % VERSION, "", "Functions:"]
    for fname in FUNCTIONS:
        r = functions[fname]
        if not r["present"]:
            lines.append("  %-18s missing" % fname)
        elif r.get("signature") == "positional":
            lines.append("  %-18s positional arguments: not tested (see To do)" % fname)
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
        lines.append("  %-6s = %-12s %s" % (name, _fmt(r["value"]), mark))
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
    _display({"text/plain": text}, {"hw3check": {"summary": summary}}, text)


def _namespace():
    ip = _ipython()
    if ip is not None:
        return ip.user_ns
    return vars(sys.modules["__main__"])
