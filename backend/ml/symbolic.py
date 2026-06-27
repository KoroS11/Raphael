"""
Symbolic Layer orchestration — runs Blue Team aggregation, Red Team
challenge, and reconciliation, returning one final annotated record
per evidence object. Pure orchestration; all decision logic lives
in ml/rules.py (reconcile_evidence) and ml/red_team.py.
"""
