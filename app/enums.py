import enum


# ---- ROLE (RBAC) ----
class RoleEnum(str, enum.Enum):
  ADMIN = "Admin"
  MANAGER = "Manager"
  EDITOR = "Editor"
  MODERATOR = "Moderator"
  PREMIUM = "Premium"
  USER = "User"