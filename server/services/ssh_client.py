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
