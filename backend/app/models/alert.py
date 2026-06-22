# backend/app/models/alert.py
"""Modelos de Alertas (Sprint 11).

Una **regla de alerta** define un umbral sobre una métrica (por conexión, y a veces
por base). El motor evalúa las métricas en vivo; si se cruza el umbral, levanta una
**alerta** con severidad y un workaround sugerido. Si la regla tiene
``auto_remediate`` y el valor llega al ``auto_threshold`` (límite máximo), el
workaround se ejecuta solo.
"""
from pydantic import BaseModel

# Métricas soportadas. Scope:
#   instancia → de performance_repo.get_metrics (DMVs de servidor)
#   base      → log_used_pct (sys.database_files de esa base)
#   disponibilidad → service_down (WinRM), instance_unreachable (no conecta)
METRICS = (
    "cpu_percent", "memory_percent", "sessions", "active_requests", "connections",
    "blocked", "locks", "log_used_pct", "service_down", "instance_unreachable",
)


class AlertRuleCreate(BaseModel):
    name: str
    connection_id: str
    database: str = ""               # requerido para métricas por base (log_used_pct)
    metric: str
    operator: str = "gt"             # gt | gte | lt | lte
    threshold: float
    severity: str = "warning"        # info | warning | critical
    suggested_workaround_key: str | None = None
    auto_remediate: bool = False
    auto_threshold: float | None = None   # límite máximo: si se cruza, ejecuta el workaround
    cooldown_seconds: int = 300
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    operator: str | None = None
    threshold: float | None = None
    severity: str | None = None
    suggested_workaround_key: str | None = None
    auto_remediate: bool | None = None
    auto_threshold: float | None = None
    cooldown_seconds: int | None = None
    enabled: bool | None = None


class AlertRule(AlertRuleCreate):
    id: str
    last_checked: str | None = None
    last_value: float | None = None
    last_triggered: str | None = None


class Alert(BaseModel):
    id: str
    rule_id: str | None = None
    connection_id: str
    source: str = ""
    metric: str
    value: float | None = None
    threshold: float | None = None
    severity: str
    title: str
    description: str = ""
    status: str = "active"           # active | acknowledged | resolved | false_alarm
    suggested_workaround_key: str | None = None
    auto_remediated: bool = False
    assigned_to: str | None = None
    created_at: str
    updated_at: str


class AlertUpdate(BaseModel):
    status: str | None = None        # acknowledged | resolved | false_alarm | active
    assigned_to: str | None = None


class AlertTemplate(BaseModel):
    metric: str
    name: str
    operator: str
    threshold: float
    severity: str
    scope: str = "instance"          # instance | database | availability
    suggested_workaround_key: str | None = None
    auto_remediate: bool = False
    auto_threshold: float | None = None
    description: str = ""


class AlertEvaluation(BaseModel):
    rule_id: str
    name: str
    metric: str
    checked: bool                    # False si no se pudo leer la métrica
    breached: bool
    value: float | None = None
    auto_remediated: bool = False
    status: str | None = None
    error: str | None = None
