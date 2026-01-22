import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from .models import ScriptExecRecord, ScriptItem

LOG_BASE_DIR = Path("logs")


def _ensure_log_dir(script_id: int) -> Path:
    date_str = datetime.utcnow().strftime("%Y%m%d")
    path = LOG_BASE_DIR / str(script_id) / date_str
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_script(
    db: Session,
    script: ScriptItem,
    params_json: Optional[str],
    operator: Optional[str],
) -> ScriptExecRecord:
    exec_record = ScriptExecRecord(
        script_id=script.id,
        status="running",
        operator=operator,
        params_json=params_json,
    )
    db.add(exec_record)
    db.commit()
    db.refresh(exec_record)

    log_dir = _ensure_log_dir(script.id)
    log_path = log_dir / f"{exec_record.id}.log"

    command = _build_command(script, params_json)

    exec_record.log_path = str(log_path)
    db.commit()

    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"Command: {command}\n")
        log_file.write(f"Start: {exec_record.start_time.isoformat()}Z\n\n")
        log_file.flush()

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            )
            assert process.stdout is not None
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()
            process.wait()
            exec_record.exit_code = process.returncode
            exec_record.status = (
                "success" if process.returncode == 0 else "fail"
            )
        except Exception as exc:  # pragma: no cover
            log_file.write(f"\n[ERROR] {exc}\n")
            exec_record.exit_code = -1
            exec_record.status = "fail"

    exec_record.end_time = datetime.utcnow()
    db.commit()
    db.refresh(exec_record)
    return exec_record


def _build_command(script: ScriptItem, params_json: Optional[str]) -> str:
    params = {}
    if params_json:
        try:
            params = json.loads(params_json)
        except json.JSONDecodeError:
            params = {}

    script_path = script.script_path
    if not os.path.isabs(script_path):
        script_path = str(Path("scripts") / script_path)

    if script.exec_command_template:
        return script.exec_command_template.format(
            script=script_path, **params
        )

    if script.script_type.lower() == "python":
        return f'python "{script_path}"'
    if script.script_type.lower() in ("powershell", "ps1"):
        return f'powershell -ExecutionPolicy Bypass -File "{script_path}"'
    if script.script_type.lower() in ("shell", "bash"):
        return f'"{script_path}"'

    return script_path

