import pytest

from rules.parser import (
  load_rules_from_yaml_text,
  Rule,
)


def test_parse_single_rule_minimal():
    yaml_text = """
id: test_rule
version: 1
trigger:
  type: schedule
  cron: "0 9 * * *"
actions:
  - type: push_notification
    template_id: morning
"""
    rules = load_rules_from_yaml_text(yaml_text)
    assert len(rules) == 1
    r = rules[0]
    assert isinstance(r, Rule)
    assert r.id == "test_rule"
    assert r.trigger.type == "schedule"
    assert r.actions[0].type == "push_notification"


def test_parse_multi_rules_and_uniqueness():
    yaml_text = """
rules:
  - id: a
    version: 1
    trigger: { type: event, name: weekly_summary_computed }
    actions:
      - type: adjust_plan_targets
  - id: b
    version: 2
    trigger: { type: schedule, cron: "0 12 * * *" }
    actions:
      - type: push_notification
        template_id: lunch
"""
    rules = load_rules_from_yaml_text(yaml_text)
    assert {r.id for r in rules} == {"a", "b"}


def test_duplicate_ids_error():
    yaml_text = """
rules:
  - id: dup
    version: 1
    trigger: { type: schedule, cron: "0 8 * * *" }
    actions:
      - type: push_notification
        template_id: t1
  - id: dup
    version: 1
    trigger: { type: schedule, cron: "0 9 * * *" }
    actions:
      - type: push_notification
        template_id: t2
"""
    with pytest.raises(ValueError):
        load_rules_from_yaml_text(yaml_text)


def test_missing_trigger_field():
    yaml_text = """
id: missing_trigger
version: 1
actions:
  - type: push_notification
    template_id: x
trigger:
  type: schedule
"""  # missing cron
    with pytest.raises(ValueError):
        load_rules_from_yaml_text(yaml_text)


def test_unknown_condition_type():
    yaml_text = """
id: cond_unknown
version: 1
trigger: { type: schedule, cron: "0 10 * * *" }
actions:
  - type: push_notification
    template_id: id
conditions:
  - type: something_else
"""
    with pytest.raises(ValueError):
        load_rules_from_yaml_text(yaml_text)
