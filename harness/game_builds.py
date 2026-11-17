"""Reviewed native game build pins for explicit copied-game preparation."""

from dataclasses import dataclass

from .asar import HarnessError


@dataclass(frozen=True)
class GameBuild:
    version: str
    commit: str
    assembly_sha256: str
    tree_sha256: str


V0_111_1 = GameBuild(
    version="v0.111.1",
    commit="cc1f9462",
    assembly_sha256="0dba5816282c6483d9305032acbe1a9be1e5e31b505421834ef7d1e786c19abf",
    tree_sha256="fa13254041eb414bef4bceba413fe23aff3e0a4dbee9a86da8cb5840aeb34be4",
)


def reviewed(build):
    """Refuse callers that supply their own unreviewed version or hashes."""
    if build != V0_111_1 or type(build) is not GameBuild:
        raise HarnessError("Unreviewed game build")
    return build
