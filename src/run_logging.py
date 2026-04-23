#!/usr/bin/env python3
import json
import os
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

DEFAULT_LOG_DIR = Path("output") / "logs"


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data: str) -> int:
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


class RunLogger:
    def __init__(self, mode: str, argv: list[str], output_dir: str | None = None):
        self.mode = mode or "default"
        self.argv = argv[:]
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_LOG_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.started_dt = datetime.now(timezone.utc)
        self.started_at_iso = self.started_dt.isoformat()
        self.started_at_epoch = time.time()
        self.run_id = self.started_dt.strftime("%Y%m%dT%H%M%SZ")
        self.base_path = self.output_dir / f"{self.mode}-{self.run_id}"
        self.meta_path = self.base_path.with_suffix(".json")
        self.out_path = self.base_path.with_suffix(".log")
        self.err_path = self.base_path.with_suffix(".error.log")

    def write_meta(self, status: str, exit_code: int | None = None, error: str = "", finished: bool = False) -> None:
        finished_dt = datetime.now(timezone.utc) if finished else None
        finished_at_iso = finished_dt.isoformat() if finished_dt else None
        duration_seconds = round(time.time() - self.started_at_epoch, 3)
        payload = {
            "run_id": self.run_id,
            "mode": self.mode,
            "command": " ".join(self.argv),
            "argv": self.argv,
            "status": status,
            "exit_code": exit_code,
            "error": error,
            "started_at_utc": self.started_at_iso,
            "finished_at_utc": finished_at_iso,
            "duration_seconds": duration_seconds,
            "cwd": os.getcwd(),
            "stdout_log": str(self.out_path),
            "stderr_log": str(self.err_path),
        }
        self.meta_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def run(self, fn: Callable[[], int]) -> int:
        self.write_meta(status="running")
        stdout_handle = self.out_path.open("w", encoding="utf-8")
        stderr_handle = self.err_path.open("w", encoding="utf-8")
        try:
            tee_out = TeeStream(sys.__stdout__, stdout_handle)
            tee_err = TeeStream(sys.__stderr__, stderr_handle)
            with redirect_stdout(tee_out), redirect_stderr(tee_err):
                try:
                    code = fn()
                except SystemExit as exc:
                    code = int(exc.code) if isinstance(exc.code, int) else 1
                    raise
                except Exception as exc:
                    traceback.print_exc()
                    self.write_meta(status="failed", exit_code=1, error=str(exc), finished=True)
                    return 1
            self.write_meta(status="finished", exit_code=code, finished=True)
            return code
        except SystemExit as exc:
            code = int(exc.code) if isinstance(exc.code, int) else 1
            self.write_meta(
                status="finished" if code == 0 else "failed",
                exit_code=code,
                error="" if code == 0 else f"SystemExit({code})",
                finished=True,
            )
            return code
        finally:
            stdout_handle.close()
            stderr_handle.close()
