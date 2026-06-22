# backend/app/routes/alerts.py
"""Alertas por umbrales (Sprint 11). Protegido por auth y auditado.

Reglas (umbrales) + feed de alertas + evaluación. La auto-remediación dirigida por
alertas vive en services/alerts.evaluate.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user
from app.models.alert import (
    Alert, AlertEvaluation, AlertRule, AlertRuleCreate, AlertRuleUpdate, AlertTemplate,
    AlertUpdate, METRICS,
)
from app.models.auth import User
from app.services import alerts, alerts_repo, audit_repo, workaround_exec

router = APIRouter(prefix="/alerts", tags=["alerts"])

_SEVERITIES = {"info", "warning", "critical"}
_OPERATORS = {"gt", "gte", "lt", "lte"}
_STATUSES = {"active", "acknowledged", "resolved", "false_alarm"}


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _validate_rule(metric: str, operator: str, severity: str, workaround_key: str | None):
    if metric not in METRICS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Métrica inválida: {metric}")
    if operator not in _OPERATORS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Operador inválido: {operator}")
    if severity not in _SEVERITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Severidad inválida: {severity}")
    if workaround_key and workaround_exec.resolve(workaround_key) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"El workaround '{workaround_key}' no existe.")


# ── Plantillas y reglas ──────────────────────────────────────────────────────

@router.get("/templates", response_model=list[AlertTemplate])
def list_templates(user: User = Depends(get_current_user)):
    return alerts.templates()


@router.get("/rules", response_model=list[AlertRule])
def list_rules(connection_id: str | None = None, user: User = Depends(get_current_user)):
    return alerts_repo.list_rules(connection_id)


@router.post("/rules", response_model=AlertRule, status_code=status.HTTP_201_CREATED)
def create_rule(body: AlertRuleCreate, request: Request, user: User = Depends(get_current_user)):
    _validate_rule(body.metric, body.operator, body.severity, body.suggested_workaround_key)
    created = alerts_repo.create_rule(body.model_dump())
    audit_repo.log(user.email or user.username, "alert.rule_create",
                   target=body.connection_id, detail=f"{body.metric} {body.operator} {body.threshold}",
                   ip=_ip(request))
    return created


@router.post("/rules/seed", response_model=list[AlertRule], status_code=status.HTTP_201_CREATED)
def seed_rules(connection_id: str, request: Request, database: str = "",
               user: User = Depends(get_current_user)):
    """Crea las reglas recomendadas para una conexión (idempotente por métrica).
    Las reglas por base (log_used_pct) solo se crean si se pasa `database`."""
    created = []
    for tpl in alerts.templates():
        db = database if tpl["scope"] == "database" else ""
        if tpl["scope"] == "database" and not database:
            continue
        if alerts_repo.has_rule_for_metric(connection_id, tpl["metric"], db):
            continue
        created.append(alerts_repo.create_rule({
            "name": tpl["name"], "connection_id": connection_id, "database": db,
            "metric": tpl["metric"], "operator": tpl["operator"], "threshold": tpl["threshold"],
            "severity": tpl["severity"], "suggested_workaround_key": tpl.get("suggested_workaround_key"),
            "auto_remediate": tpl.get("auto_remediate", False), "auto_threshold": tpl.get("auto_threshold"),
            "auto_after_seconds": tpl.get("auto_after_seconds"),
            "cooldown_seconds": 300, "enabled": True,
        }))
    audit_repo.log(user.email or user.username, "alert.rule_seed",
                   target=connection_id, detail=f"{len(created)} reglas", ip=_ip(request))
    return created


@router.put("/rules/{rule_id}", response_model=AlertRule)
def update_rule(rule_id: str, body: AlertRuleUpdate, request: Request,
                user: User = Depends(get_current_user)):
    if body.operator and body.operator not in _OPERATORS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operador inválido")
    if body.suggested_workaround_key and workaround_exec.resolve(body.suggested_workaround_key) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workaround inexistente")
    updated = alerts_repo.update_rule(rule_id, body.model_dump())
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regla no encontrada.")
    audit_repo.log(user.email or user.username, "alert.rule_update", target=rule_id, ip=_ip(request))
    return updated


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: str, request: Request, user: User = Depends(get_current_user)):
    if not alerts_repo.delete_rule(rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regla no encontrada.")
    audit_repo.log(user.email or user.username, "alert.rule_delete", target=rule_id, ip=_ip(request))


# ── Feed de alertas ──────────────────────────────────────────────────────────

@router.get("/count")
def count_active(user: User = Depends(get_current_user)):
    return {"active": alerts_repo.count_active()}


@router.post("/evaluate", response_model=list[AlertEvaluation])
def evaluate_now(request: Request, user: User = Depends(get_current_user)):
    actor = user.email or user.username
    results = alerts.evaluate(actor)
    fired = sum(1 for r in results if r.get("breached"))
    audit_repo.log(actor, "alert.evaluate", detail=f"{len(results)} reglas · {fired} en alerta",
                   ip=_ip(request))
    return results


@router.get("", response_model=list[Alert])
def list_alerts(status: str | None = None, user: User = Depends(get_current_user)):
    return alerts_repo.list_alerts(status)


@router.patch("/{alert_id}", response_model=Alert)
def update_alert(alert_id: str, body: AlertUpdate, request: Request,
                 user: User = Depends(get_current_user)):
    if body.status and body.status not in _STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Estado inválido: {body.status}")
    updated = alerts_repo.set_status(alert_id, body.status, body.assigned_to)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada.")
    audit_repo.log(user.email or user.username, "alert.update", target=alert_id,
                   detail=body.status or "asignación", ip=_ip(request))
    return updated
