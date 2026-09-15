import os, sys
from graph import run

if __name__ == "__main__":
    os.environ["DRY_RUN"] = "1" if "--dry-run" in sys.argv else "0"
    out = run()
    for line in out["log"]:
        print(line)