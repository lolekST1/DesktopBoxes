"""Lista zainstalowanych aplikacji z menu Start (klasyczne + UWP/Sklep).

Korzysta z wbudowanego polecenia PowerShell `Get-StartApps`, które zwraca te same
aplikacje, które widać w menu Start i które można przypiąć do paska zadań — wraz z
ich AppUserModelID. Dzięki temu można dodać do boxa aplikacje, których nie da się
przeciągnąć (np. przypięte na pasku zadań)."""
import json
import subprocess

CREATE_NO_WINDOW = 0x08000000

_cache = None

_PS_COMMAND = (
    "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
    "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress"
)


def list_start_apps(refresh: bool = False) -> list:
    """Zwraca posortowaną listę {name, path} aplikacji z menu Start.

    path ma postać 'shell:AppsFolder\\<AppID>' i jest uruchamiany przez Eksplorator.
    """
    global _cache
    if _cache is not None and not refresh:
        return _cache
    apps = []
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_COMMAND],
            capture_output=True, text=True, encoding="utf-8", timeout=25,
            creationflags=CREATE_NO_WINDOW,
        )
        data = json.loads(proc.stdout) if proc.stdout.strip() else []
        if isinstance(data, dict):
            data = [data]
        seen = set()
        for d in data:
            name = (d.get("Name") or "").strip()
            app_id = (d.get("AppID") or "").strip()
            if not name or not app_id or app_id in seen:
                continue
            seen.add(app_id)
            apps.append({"name": name, "path": "shell:AppsFolder\\" + app_id})
        apps.sort(key=lambda a: a["name"].lower())
    except Exception:
        apps = []
    _cache = apps
    return apps
