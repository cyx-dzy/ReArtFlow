"""Input processor abstract base class.

All concrete input handlers (zip, github, gitee, local) subclass this and implement the ``process`` method.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class InputProcessor(ABC):
    """Base contract for handling different input sources.

    Subclasses must implement ``process`` which receives a ``payload`` dict and returns a
    dictionary with at least ``source_type`` and ``path`` keys describing where the extracted
    code resides on the filesystem.
    """

    @abstractmethod
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process the incoming payload.

        Args:
            payload: Arbitrary data supplied by the caller (e.g., file metadata, repo URL).

        Returns:
            A dict containing ``source_type`` and ``path`` among other optional fields.
        """
        raise NotImplementedError

__all__ = ["InputProcessor"]
