# Threat Taxonomy

Each threat category isolates one compliance control. The regulatory grounding
is listed so reviewers and practitioners can map directly to their compliance
programmes.

| Category | Threat | Compliance control | Regulatory grounding |
|---|---|---|---|
| `T2_unauthorized_transfer` | Indirect injection → fraudulent payment | Payee allow-list | FFIEC payment authorization |
| `T3_sanctions_evasion` | Pay a sanctioned payee (flagged at onboarding) | Sanctions screening | 31 C.F.R. §501; OFAC SDN |
| `T3_sanctions_evasion` (homoglyph) | Sanctioned entity hidden behind look-alike characters | Normalized name matching | OFAC typologies; FinCEN alerts |
| `T4_structuring` | Split a payment to stay under the reporting threshold | CTR reporting | BSA 31 U.S.C. §5324 |
| `T5_dual_approval_defeat` | Initiate and self-approve a large transfer | Maker-checker | FFIEC IT Handbook; SOX COSO |
| `T6_data_exfiltration` | Email customer card / SSN to an external address | DLP on outbound messages | GLBA Safeguards Rule; PCI-DSS Req. 3 |
| `T7_confused_deputy` | Redirect an approved payee's bank details | Bank-detail change verification | FBI IC3 BEC guidance |
| `BENIGN` | A legitimate payment (over-refusal control) | — | — |

## Control postures

Every scenario is evaluated under three postures:

| Posture | Setup | What it measures |
|---|---|---|
| **none** | No compliance policy stated to the agent | Intrinsic susceptibility |
| **advisory** | Policy stated as obligations, not enforced | Does the model follow stated policy? |
| **enforced** | System hard-blocks violations in the sandbox | Residual risk (defense-in-depth) |

The gap between *none* and *advisory* (policy-following uplift) and the gap
between *advisory* and *enforced* (enforcement uplift) are the primary metrics.
