# backend/app/services/host_control.py
"""Control del host Windows vía WinRM (Sprint 10.1).

Permite iniciar el **servicio de SQL Server a nivel sistema operativo** cuando el
motor está caído (en ese estado no hay conexión T-SQL posible). El backend corre
en Docker (Linux), así que el canal es **WinRM**: se conecta a la máquina Windows
(``host.docker.internal`` o IP) con credenciales Windows y ejecuta PowerShell.

Requiere en la máquina Windows: ``Enable-PSRemoting`` y un usuario con permiso para
manejar servicios. El import de ``winrm`` es **lazy** (dentro de cada función) para
que la ausencia de la dependencia dé un error claro y los tests puedan mockear sin
instalarla.

⚠️ SEGURIDAD: las credenciales Windows se guardan en Mongo en texto plano (dev/TFI),
igual que las de SQL. En producción: cifrar / Azure Key Vault.
"""


def _session(cfg: dict):
    """Crea una sesión WinRM a partir de la config de host-control."""
    import winrm  # import lazy: solo si realmente se usa el control de host

    host = cfg["host"]
    port = cfg.get("port", 5985)
    transport = cfg.get("transport", "ntlm")
    scheme = "https" if int(port) == 5986 else "http"
    endpoint = f"{scheme}://{host}:{port}/wsman"
    return winrm.Session(
        endpoint,
        auth=(cfg["username"], cfg["password"]),
        transport=transport,
        server_cert_validation="ignore",
    )


def _run_ps(cfg: dict, script: str) -> str:
    """Ejecuta un script PowerShell por WinRM. Devuelve stdout (texto, sin espacios)."""
    session = _session(cfg)
    result = session.run_ps(script)
    if result.status_code != 0:
        err = (result.std_err or b"").decode("utf-8", "ignore").strip()
        raise RuntimeError(err or f"WinRM devolvió código {result.status_code}")
    return (result.std_out or b"").decode("utf-8", "ignore").strip()


def service_status(cfg: dict) -> dict:
    """Estado del servicio Windows (Get-Service). Devuelve {service_name, status}."""
    svc = cfg["service_name"]
    status = _run_ps(cfg, f"(Get-Service -Name '{svc}').Status")
    return {"service_name": svc, "status": status or "Unknown"}


def start_service(cfg: dict) -> dict:
    """Inicia el servicio Windows (Start-Service) y devuelve el estado resultante."""
    svc = cfg["service_name"]
    status = _run_ps(
        cfg,
        f"Start-Service -Name '{svc}'; Start-Sleep -Seconds 1; (Get-Service -Name '{svc}').Status",
    )
    return {"service_name": svc, "status": status or "Unknown"}
