"""Fallback runner when pytest is unavailable (offline). Normal use: `pytest`."""
import importlib, inspect, os, sys, traceback
sys.path.insert(0, os.path.dirname(__file__))
class _P:  # minimal pytest shim
    class raises:
        def __init__(s, exc): s.exc = exc
        def __enter__(s): return s
        def __exit__(s, t, v, tb):
            assert t and issubclass(t, s.exc), "did not raise"; s.value = v; return True
sys.modules.setdefault("pytest", type(sys)("pytest")); sys.modules["pytest"].raises = _P.raises
sys.modules["pytest"].fixture = lambda *a, **k: (lambda f: f)
sys.modules["pytest"].importorskip = lambda m: (_ for _ in ()).throw(ImportError(m))
class MP:
    def __init__(s): s._undo = []
    def setenv(s, k, v): os.environ[k] = v
    def delenv(s, k): os.environ.pop(k, None)
    def setitem(s, d, k, v): s._undo.append((d, k, d.get(k, None))); d[k] = v
    def setattr(s, o, n, v): s._undo.append((o, n, getattr(o, n))); setattr(o, n, v)
fails = 0
for mod in ["test_rule_engine", "test_evidence_validator", "test_candidate_extractor", "test_extractor", "test_evaluation", "test_images_security_insights", "test_integrations"]:
    m = importlib.import_module("tests." + mod)
    for n, f in inspect.getmembers(m, inspect.isfunction):
        if n.startswith("test_"):
            saved = dict(os.environ)
            try:
                mp = MP(); params = inspect.signature(f).parameters; kw = {}
                if "monkeypatch" in params: kw["monkeypatch"] = mp
                if "tmp_path" in params: import tempfile, pathlib; kw["tmp_path"] = pathlib.Path(tempfile.mkdtemp())
                f(**kw); print("PASS", mod, n)
            except Exception:
                fails += 1; print("FAIL", mod, n); traceback.print_exc()
            for o, n, old in reversed(mp._undo):
                if isinstance(o, dict):
                    (o.__setitem__(n, old) if old is not None else o.pop(n, None))
                else: setattr(o, n, old)
            os.environ.clear(); os.environ.update(saved)
print("failures:", fails); sys.exit(1 if fails else 0)
