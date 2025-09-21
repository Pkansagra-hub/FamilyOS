from __future__ import annotations
import argparse, json, sys
from typing import List
from ..rbac import RbacEngine, RoleDef, Binding
from ..consent import ConsentStore, ConsentRecord
from ..abac import AbacEngine, AbacContext, ActorAttrs, DeviceAttrs, EnvAttrs
from ..space_policy import SpacePolicy, ShareRequest
from ..config_loader import load_policy_config
from ..audit import AuditLogger

def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))

def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="policyctl", description="Policy layer CLI")
    p.add_argument("--roles-db", default="/tmp/policy_roles.json")
    p.add_argument("--consent-db", default="/tmp/policy_consent.json")
    p.add_argument("--audit-dir", default="/tmp/policy_audit")
    sub = p.add_subparsers(dest="cmd", required=True)

    # roles
    rp = sub.add_parser("role-define")
    rp.add_argument("name")
    rp.add_argument("--cap", action="append", required=True)

    rbp = sub.add_parser("bind")
    rbp.add_argument("principal_id"); rbp.add_argument("role"); rbp.add_argument("space_id")

    rub = sub.add_parser("unbind")
    rub.add_argument("principal_id"); rub.add_argument("role"); rub.add_argument("space_id")

    lcp = sub.add_parser("caps"); lcp.add_argument("principal_id"); lcp.add_argument("space_id")

    # consent
    cg = sub.add_parser("consent-grant")
    cg.add_argument("from_space"); cg.add_argument("to_space"); cg.add_argument("purpose"); cg.add_argument("granted_by")
    cg.add_argument("--expires-at")

    ck = sub.add_parser("consent-check")
    ck.add_argument("from_space"); ck.add_argument("to_space"); ck.add_argument("purpose")

    # share evaluate
    sp = sub.add_parser("eval-share")
    sp.add_argument("--config")
    sp.add_argument("op", choices=["REFER","PROJECT","DETACH","UNDO"])
    sp.add_argument("actor_id"); sp.add_argument("from_space"); sp.add_argument("--to-space")
    sp.add_argument("--band", default="GREEN")
    sp.add_argument("--tags", nargs="*", default=[])
    sp.add_argument("--is-minor", action="store_true")
    sp.add_argument("--device-trust", default="trusted")
    sp.add_argument("--time", type=float, default=12.0)
    sp.add_argument("--arousal", type=float, default=0.5)
    sp.add_argument("--safety", type=float, default=0.0)

    args = p.parse_args(argv)

    rbac = RbacEngine(args.roles_db)
    consent = ConsentStore(args.consent_db)
    abac = AbacEngine()
    audit = AuditLogger(args.audit_dir)

    if args.cmd == "role-define":
        rbac.define_role(RoleDef(args.name, args.cap)); print("ok"); return 0
    if args.cmd == "bind":
        rbac.bind(Binding(args.principal_id, args.role, args.space_id)); print("ok"); return 0
    if args.cmd == "unbind":
        rbac.unbind(args.principal_id, args.role, args.space_id); print("ok"); return 0
    if args.cmd == "caps":
        _print(sorted(rbac.list_caps(args.principal_id, args.space_id))); return 0
    if args.cmd == "consent-grant":
        consent.grant(ConsentRecord(args.from_space,args.to_space,args.purpose,args.granted_by,args.expires_at)); print("ok"); return 0
    if args.cmd == "consent-check":
        _print({"has": consent.has_consent(args.from_space, args.to_space, args.purpose)}); return 0
    if args.cmd == "eval-share":
        band_defaults = {}
        if args.config:
            cfg = load_policy_config(args.config)
            band_defaults = cfg.band_defaults
        pol = SpacePolicy(rbac, abac, consent, band_defaults=band_defaults)
        abac_ctx = AbacContext(
            ActorAttrs(args.actor_id, is_minor=args.is_minor),
            DeviceAttrs("device", trust=args.device_trust),
            EnvAttrs(time_of_day_hours=args.time, arousal=args.arousal, safety_pressure=args.safety),
        )
        dec = pol.evaluate_share(ShareRequest(args.op, args.actor_id, args.from_space, args.to_space, args.band, args.tags), abac_ctx)
        audit.log({"type":"POLICY_DECISION","actor_id":args.actor_id,"action":args.op,"from":args.from_space,"to":args.to_space,"decision":dec.decision,"reasons":dec.reasons})
        _print(dec.__dict__); return 0

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
