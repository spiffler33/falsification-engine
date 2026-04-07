"""v9 contract schemas — Phase 0: contract-hardening layer.

These schemas define the machine contract for the v9 semantic compiler.
They are the canonical interface between:
  - the Haiku compiler (upstream producer)
  - the deterministic runtime evaluator (downstream consumer)
  - the validator (contract enforcer)

No runtime code lives here. Only data shapes and contracts.
"""
