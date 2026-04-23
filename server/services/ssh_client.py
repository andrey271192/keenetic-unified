"""SSH client for executing commands on routers. Uses root/keenetic by default."""
import asyncio, logging
from .. import config
logger = logging.getLogger("keenetic")

async def ssh_exec(host: str, command: str, user: str = None, password: str = None, timeout: int = 15) -> str:
    """Execute SSH command via sshpass + ssh. Returns stdout or error string."""
    if not user: user = config.SSH_USER
    if not password: password = config.SSH_PASS
    try:
        proc = await asyncio.create_subprocess_exec(
            "sshpass", "-p", password,
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            f"{user}@{host}", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode == 0:
            return out or "(пусто)"
        return f"Ошибка (код {proc.returncode}):\n{err or out}"
    except asyncio.TimeoutError:
        return "⏰ Таймаут SSH (15 сек)"
    except FileNotFoundError:
        return "❌ sshpass не установлен. apt install sshpass"
    except Exception as e:
        return f"❌ SSH ошибка: {e}"

async def ssh_exec_verbose(host: str, command: str, user: str = None, password: str = None, timeout: int = 60) -> dict:
    """Execute SSH command and return full details: stdout, stderr, exit_code, hostname."""
    if not user: user = config.SSH_USER
    if not password: password = config.SSH_PASS
    # Wrap command: capture exit code and hostname explicitly
    wrapped = f"echo \"[$(hostname)] $(date '+%H:%M:%S')\"; ({command}); _ec=$?; echo \"--- exit: $_ec ---\"; exit $_ec"
    try:
        proc = await asyncio.create_subprocess_exec(
            "sshpass", "-p", password,
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            f"{user}@{host}", wrapped,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        code = proc.returncode
        return {
            "exit_code": code,
            "output": out,
            "stderr": err,
            "ok": code == 0,
        }
    except asyncio.TimeoutError:
        return {"exit_code": -1, "output": "⏰ Таймаут SSH", "stderr": "", "ok": False}
    except FileNotFoundError:
        return {"exit_code": -1, "output": "❌ sshpass не установлен", "stderr": "", "ok": False}
    except Exception as e:
        return {"exit_code": -1, "output": f"❌ SSH ошибка: {e}", "stderr": "", "ok": False}
