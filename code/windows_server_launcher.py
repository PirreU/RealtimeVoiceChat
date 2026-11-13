import os
import runpy
import sys
import traceback
from pathlib import Path


def main() -> None:
    code_directory = Path(__file__).resolve().parent
    os.chdir(code_directory)
    sys.path.insert(0, str(code_directory))
    exit_code = 0

    try:
        runpy.run_path(str(code_directory / "server.py"), run_name="__main__")
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except SystemExit as error:
        if error.code not in (None, 0):
            exit_code = error.code if isinstance(error.code, int) else 1
            traceback.print_exc()
    except Exception:
        exit_code = 1
        traceback.print_exc()

    if exit_code == 0:
        print("\nServer stopped.")
    input("\nPress Enter to close this window...")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
