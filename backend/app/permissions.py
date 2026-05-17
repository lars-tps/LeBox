"""Single chokepoint for authorization decisions.

Today the rule is "owner only." When sharing arrives, add a `permissions`
table and change THIS function — call sites stay the same.
"""

from typing import Literal
from app.models import File, Folder, User


Action = Literal["read", "write", "delete"]


def can_access_file(user: User, file: File, action: Action = "read") -> bool:  # noqa: ARG001
    return file.owner_user_id == user.id


def can_access_folder(user: User, folder: Folder, action: Action = "read") -> bool:  # noqa: ARG001
    return folder.owner_user_id == user.id
