"""Temporary proof driver: time the 1 MiB ConPTY paste and run the test N times."""
import multiprocessing, os, re, subprocess, sys, time

def burn():
    while True:
        pass

def main():
    load = os.environ["PROOF_LOAD"] == "loaded"
    burners = []
    if load:
        burners = [multiprocessing.Process(target=burn, daemon=True) for _ in range(os.cpu_count() * 2)]
        for b in burners:
            b.start()
    print(f"LEG {os.environ['PROOF_LEG']} load={load} cpus={os.cpu_count()} burners={len(burners)}", flush=True)
    # Raw timing of the product write (no test bounds) via the test interpreter.
    timing = r'''
import asyncio, sys, time
from hermes_cli.win_pty_bridge import WinPtyBridge
async def main():
    for i in range(3):
        b = WinPtyBridge.spawn([sys.executable, "-c", "import time; time.sleep(60)"])
        paste = b"".join(b"%05d %s\r" % (n, b"x" * 57) for n in range(16384))
        t = time.monotonic(); ok = await b.write(paste, timeout=None); dt = time.monotonic() - t
        print(f"TIMING write_1MiB ok={ok} seconds={dt:.2f}", flush=True)
        b.close()
asyncio.run(main())
'''
    py = os.environ.get("HERMES_PROOF_PY")
    passed = failed = 0
    for i in range(8):
        r = subprocess.run(["bash", "scripts/run_tests.sh",
                            "tests/hermes_cli/test_win_pty_bridge.py", "--", "-m", "platforms and not integration",
                            "-v", "--tb=line", "-k", "lands_at_once"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        rows = sorted(set(re.findall(r"test_paste_to_a_program_that_is_not_reading_lands_at_once (PASSED|FAILED)", r.stdout)))
        line = f"RUN {i} exit={r.returncode} rows={rows}"
        print(line, flush=True)
        if r.returncode == 0 and rows == ["PASSED"]:
            passed += 1
        else:
            failed += 1
            print(r.stdout[-3000:], flush=True)
    try:
        t = subprocess.run([sys.executable, "-c", timing], capture_output=True, text=True, timeout=300)
        print(t.stdout, t.stderr[-2000:], flush=True)
    except Exception as e:
        print("TIMING error", e)
    print(f"RESULT leg={os.environ['PROOF_LEG']} load={load} passed={passed} failed={failed}", flush=True)
    for b in burners:
        b.terminate()
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
