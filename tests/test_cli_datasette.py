from typer.testing import CliRunner

from openrightofway.cli import app
from openrightofway.core.config import load_config


def test_db_serve_print_cmd():
    runner = CliRunner()
    res = runner.invoke(app, ["db-serve", "--print-cmd"])
    assert res.exit_code == 0
    out = res.stdout.strip()
    assert "datasette serve" in out
    cfg = load_config()
    assert cfg.app.work_orders_db in out

