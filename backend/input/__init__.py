"""Input package exposing concrete processors."""

from .processor import InputProcessor
from .zip_handler import ZipInputProcessor
from .github_handler import GitHubInputProcessor
from .gitee_handler import GiteeInputProcessor
from .local_handler import LocalPathInputProcessor
