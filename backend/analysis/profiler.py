import cProfile, pstats, io, runpy
from pathlib import Path
import pstats

def run_profile_on_example(path):
    # Try both relative and absolute paths
    p = Path(path)
    if not p.is_absolute():
        # Try relative to backend directory
        backend_dir = Path(__file__).resolve().parent.parent
        p = (backend_dir / path).resolve()
    if not p.exists():
        return {'error': f'Path not found: {p}'}
    main = p / 'main.py'
    if not main.exists():
        return {'error': f'main.py not found in {p}'}
    pr = cProfile.Profile()
    try:
        pr.enable()
        runpy.run_path(str(main), run_name='__main__')
    except SystemExit:
        pass
    except Exception as e:
        # Return error while still producing whatever profile we captured so far
        pr.disable()
        return {"error": str(e)}
    finally:
        try:
            pr.disable()
        except Exception:
            pass
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    return {'raw': s.getvalue()}
