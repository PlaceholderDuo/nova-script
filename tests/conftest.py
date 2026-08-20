"""Nova-Script test collection config.

`test_e2e_virtualizer.py` is a standalone end-to-end script (spawns the
virtualizer server + engine subprocesses and drives them over WebSocket). It
is intentionally NOT pytest-structured, so keep it out of collection. Run it
directly with:

    .venv/bin/python tests/test_e2e_virtualizer.py

The in-process virtual-harness equivalents live in test_engine_integration.py
and test_light_show_integration.py.
"""

collect_ignore = ["test_e2e_virtualizer.py"]