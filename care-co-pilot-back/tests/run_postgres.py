"""Ejecuta integración en un clúster PostgreSQL efímero; nunca usa la app DB."""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    binaries = {}
    for name in ("initdb", "pg_ctl", "createdb"):
        binary = shutil.which(name)
        if not binary:
            raise RuntimeError(f"Instala PostgreSQL local: falta {name}.")
        binaries[name] = binary
    # Reservar un puerto libre; si otro proceso lo ocupa después, pg_ctl falla
    # y no se ejecutan pruebas contra ese proceso.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="copilot_pg_") as temp:
        data = str(Path(temp) / "data")
        log = str(Path(temp) / "postgres.log")
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("PG")
            and key not in {"DATABASE_URL", "TEST_DATABASE_URL", "JWT_SECRET_KEY"}
        }
        # Solo datos ficticios; sin contraseña, trust restringido al loopback.
        subprocess.run([
            binaries["initdb"], "-D", data, "-U", "copilot_test",
            "--auth=trust", "--no-locale", "--encoding=UTF8",
        ], env=env, check=True, stdout=subprocess.DEVNULL)
        started = False
        try:
            subprocess.run([
                binaries["pg_ctl"], "-D", data, "-l", log, "-w", "start",
                "-o", f"-h 127.0.0.1 -p {port} -k {temp} -c fsync=off",
            ], env=env, check=True, stdout=subprocess.DEVNULL)
            started = True
            subprocess.run([
                binaries["createdb"], "-h", "127.0.0.1", "-p", str(port),
                "-U", "copilot_test", "copilot_test",
            ], env=env, check=True)
            env.update({
                "APP_ENV": "test",
                "TEST_POSTGRES_ALLOW_MIGRATIONS": "1",
                "TEST_DATABASE_URL": (
                    f"postgresql+psycopg://copilot_test@127.0.0.1:{port}/copilot_test"
                ),
            })
            return subprocess.run([
                sys.executable, "-m", "unittest", "discover",
                "-s", "tests", "-p", "test_postgres*.py", "-v",
            ], cwd=ROOT, env=env).returncode
        finally:
            if started:
                subprocess.run([
                    binaries["pg_ctl"], "-D", data, "-w", "stop", "-m", "immediate",
                ], env=env, check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.exit(main())
