"""Guarded output-directory preparation.

Earlier versions of `cli demo --out DIR` ran `shutil.rmtree(DIR)` on whatever path the user gave,
which silently destroyed unrelated files (reproduced during the v1.0.0 audit). This helper only
reuses a directory that is empty or demonstrably a previous run of the *same* ImmunoMesh command,
and then removes only the files that command is known to generate — never the whole tree.
"""
from __future__ import annotations
from collections.abc import Callable, Iterable
from pathlib import Path


class UnsafeOutputDir(RuntimeError):
    """Raised instead of deleting anything when the target directory is not clearly ours."""


def prepare_output_dir(out: str | Path, is_previous_run: Callable[[Path], bool],
                       generated_names: Iterable[str]) -> Path:
    path = Path(out).expanduser().resolve()
    forbidden = {Path.cwd().resolve(), Path.home().resolve(), Path(path.anchor)}
    if path in forbidden:
        raise UnsafeOutputDir(f"refusing to use {path} as an output directory (cwd, home or filesystem root)")
    if path.exists() and not path.is_dir():
        raise UnsafeOutputDir(f"{path} exists and is not a directory")
    if path.exists() and any(path.iterdir()):
        if not is_previous_run(path):
            raise UnsafeOutputDir(
                f"{path} is not empty and does not look like a previous run of this command; "
                "nothing was deleted. Choose an empty/new directory or remove it yourself.")
        for name in generated_names:           # remove only files this command itself generates
            f = path / name
            if f.is_file():
                f.unlink()
    path.mkdir(parents=True, exist_ok=True)
    return path
