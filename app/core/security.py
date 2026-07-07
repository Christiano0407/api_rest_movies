"""
  Security utilities: JWT tokens, password hashing, cookie helpers.
    # ─── Password | Encriptado (bcrypt) | Hash (Hashed | HASHEANDO password  | SALT ───────── #
    # - Un hash es una función matemática: 
    # - bcrypt es un algoritmo especializado de hashing para passwords. [Contiene  salt]
    # - Un salt es un valor aleatorio agregado al password.
    # =======
    # Hash	    Función matemática
    # Hashing	Proceso de aplicar hash
    # Hashed	Resultado ya procesado
    # bcrypt	Algoritmo hashing especializado
    # =======  
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Cookie, Depends