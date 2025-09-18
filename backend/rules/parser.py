"""Rule Engine DSL Parser (MVP)

Parsa file YAML contenenti definizioni di regole di notifica / adattamento.

Supporta due formati:
1) Singola regola (chiavi top-level: id, trigger, actions...)
2) File multi-regola con chiave root `rules: [ ... ]`

Validazioni principali implementate (vedi docs/rule_engine_DSL.md):
- id unico
- actions non vuoto
- trigger coerente (schedule richiede cron, event richiede name)
- condition/action type riconosciuti
- throttle.window_hours >=1 se presente

Nota: condition e action sono dataclass generiche; la logica runtime è altrove.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import yaml

SUPPORTED_CONDITION_TYPES = {
    "no_meal_logged_in_window",
    "user_goal_active",
    "deviation_over_threshold",
    "adherence_samples_min",
}

SUPPORTED_ACTION_TYPES = {
    "push_notification",
    "adjust_plan_targets",
}


@dataclass
class Trigger:
    type: str  # schedule|event
    cron: Optional[str] = None
    name: Optional[str] = None

    def validate(self) -> None:
        if self.type not in ("schedule", "event"):
            raise ValueError(f"Unsupported trigger.type: {self.type}")
        if self.type == "schedule" and not self.cron:
            raise ValueError("schedule trigger requires 'cron'")
        if self.type == "event" and not self.name:
            raise ValueError("event trigger requires 'name'")


@dataclass
class Condition:
    type: str
    params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.type not in SUPPORTED_CONDITION_TYPES:
            raise ValueError(f"Unknown condition type: {self.type}")
        # Basic param presence checks (minimal; business logic can expand)
        if self.type == "no_meal_logged_in_window":
            for k in ("meal_type", "window_hours"):
                if k not in self.params:
                    raise ValueError(
                        f"Condition {self.type} missing param '{k}'"
                    )
        elif self.type == "deviation_over_threshold":
            for k in (
                "metric",
                "window_days",
                "threshold_pct",
                "direction",
            ):
                if k not in self.params:
                    raise ValueError(
                        f"Condition {self.type} missing param '{k}'"
                    )


@dataclass
class Action:
    type: str
    params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.type not in SUPPORTED_ACTION_TYPES:
            raise ValueError(f"Unknown action type: {self.type}")
        if self.type == "push_notification":
            if "template_id" not in self.params:
                raise ValueError(
                    "push_notification action requires 'template_id'"
                )
        elif self.type == "adjust_plan_targets":
            # optional params; ulteriori vincoli possibili in futuro
            return


@dataclass
class Throttle:
    window_hours: int

    def validate(self) -> None:
        if self.window_hours < 1:
            raise ValueError("throttle.window_hours must be >=1")


@dataclass
class Rule:
    id: str
    version: int
    trigger: Trigger
    actions: List[Action]
    conditions: List[Condition] = field(default_factory=list)
    throttle: Optional[Throttle] = None
    priority: int = 100
    enabled: bool = True
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.id:
            raise ValueError("Rule id required")
        if not self.actions:
            raise ValueError(f"Rule {self.id} has no actions")
        self.trigger.validate()
        seen_conditions = set()
        for c in self.conditions:
            key = (c.type, tuple(sorted(c.params.items())))
            if key in seen_conditions:
                msg = (
                    f"Duplicate identical condition in rule {self.id}: "
                    f"{c.type}"
                )
                raise ValueError(msg)
            seen_conditions.add(key)
            c.validate()
        for a in self.actions:
            a.validate()
        if self.throttle:
            self.throttle.validate()


def _build_trigger(d: Dict[str, Any]) -> Trigger:
    t = d.get("type") or ""
    return Trigger(type=str(t), cron=d.get("cron"), name=d.get("name"))


def _build_conditions(raw_list: List[Dict[str, Any]]) -> List[Condition]:
    result: List[Condition] = []
    for c in raw_list:
        ct_raw = c.get("type")
        ct = str(ct_raw) if ct_raw is not None else ""
        params = {k: v for k, v in c.items() if k != "type"}
        result.append(Condition(type=ct, params=params))
    return result


def _build_actions(raw_list: List[Dict[str, Any]]) -> List[Action]:
    result: List[Action] = []
    for a in raw_list:
        at_raw = a.get("type")
        at = str(at_raw) if at_raw is not None else ""
        params = {k: v for k, v in a.items() if k != "type"}
        result.append(Action(type=at, params=params))
    return result


def _build_throttle(d: Optional[Dict[str, Any]]) -> Optional[Throttle]:
    if not d:
        return None
    return Throttle(window_hours=int(d.get("window_hours", 0)))


def _parse_rule(data: Dict[str, Any]) -> Rule:
    trigger = _build_trigger(data.get("trigger", {}))
    conditions = _build_conditions(data.get("conditions", []))
    actions = _build_actions(data.get("actions", []))
    throttle = _build_throttle(data.get("throttle"))
    rule = Rule(
        id=data.get("id", ""),
        version=int(data.get("version", 1)),
        trigger=trigger,
        conditions=conditions,
        actions=actions,
        throttle=throttle,
        priority=int(data.get("priority", 100)),
        enabled=bool(data.get("enabled", True)),
        description=data.get("description"),
        metadata=data.get("metadata", {}) or {},
    )
    rule.validate()
    return rule


def load_rules_from_yaml_text(yaml_text: str) -> List[Rule]:
    """Parsa YAML string e restituisce lista di Rule."""
    data = yaml.safe_load(yaml_text) or {}
    rules: List[Rule] = []
    if "rules" in data and isinstance(data["rules"], list):
        for item in data["rules"]:
            rules.append(_parse_rule(item))
    else:
        # assume single rule definition
        rules.append(_parse_rule(data))

    # id uniqueness check
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate rule ids detected")
    return rules


def load_rules(path: str) -> List[Rule]:
    """Carica regole da file path."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return load_rules_from_yaml_text(content)


__all__ = [
    "Rule",
    "Trigger",
    "Condition",
    "Action",
    "Throttle",
    "load_rules",
    "load_rules_from_yaml_text",
]
