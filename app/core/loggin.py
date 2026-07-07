""" Structured logging configuration using structlog. | History of the Process """

from __future__ import annotations

import logging
import sys

import structlog


# ==== Configure Logging ==== ---------------------------------------------------------------------
def configure_logging(log_level:str="INFO", environment:str="development") -> None: 
    """
      Configure structlog for JSON (prod) or pretty console (dev) output 
      (Configurar structlog para salida JSON (prod) o consola bonita (dev))
    """
    shared_processors: list[structlog.types.Processor] = [ 
        structlog.contextvars.merge_contextvars, 
        structlog.stdlib.add_logger_name, 
        structlog.stdlib.add_log_level, 
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"), 
        structlog.processors.StackInfoRenderer(),
    ]

    if environment == "development": 
        renderer : structlog.types.Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure( 
        processors=[
            *shared_processors, 
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter
        ], 
        wrapper_class=structlog.stdlib.BoundLogger, 
        context_class=dict, 
        logger_factory=structlog.stdlib.LoggerFactory(), 
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors, 
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta, 
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO)) # --- Log History ---

    for lib in ("uvicorn.access", "sqlalchemy.engine", "async"):
          logging.getLogger(lib).setLevel(logging.WARNING)

      


## === See Logging - History | Event - streaming === 