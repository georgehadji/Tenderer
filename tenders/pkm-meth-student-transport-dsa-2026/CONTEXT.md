# tenders/pkm-meth-student-transport-dsa-2026/: CONTEXT

ΔΣΑ Μεταφοράς Μαθητών Μ.Ε. Θεσσαλονίκης, school years 2026–27 to 2028–29. Covers category Β (Ε.Δ.Χ., taxi) only for now.

**Source:** Περιφέρεια Κεντρικής Μακεδονίας · ΑΔΑ `ΨΡΘ97ΛΛ-ΕΕΚ` · ΚΗΜΔΗΣ `26PROC018591823` · 06/03/2026 · DPS open until 30/06/2029
[ΠΚΜ page](https://www.pkm.gov.gr/prokiryxi-dynamikou-systimatos-agoronkata-to-arthro-33-tou-n-4412-2016gia-tin-anathesi-ypiresion-metaforas-mathiton-dimosion-scholeion-chorikis-armodiotitas-m-e-thessalonikis-diarkeias-trion-3-s/) · [Διαύγεια](https://diavgeia.gov.gr/doc/ΨΡΘ97ΛΛ-ΕΕΚ)

| File | Contains / does |
|---|---|
| `sop.md` | Workflow (Greek), with the `§` of each step. Phase Α: one-off admission to the ΔΣΑ (steps Α0–Α3, Α∞). Phase Β: each invitation, from route filter to go/no-go, dossier, offer, provisional award and contract (steps Β1–Β10). Phase Γ: 3-year contract execution and payments. |
| `requirements.csv` | 26 requirements and documents (R1–R26): what, which step, issuer, validity rule, `§`. Follows the schema in `tenders/CONTEXT.md`. R24–R26 (vehicle lease, escort medical certificate, vehicle–driver–escort table) were added on 24/09/2026 from §4.3.1.1, §5.3.2 Β.4.2 and §5.5. |
| `desk-research-2026.md` | Step 1 desk research (Greek), state on 23/09/2026: the 2026 taxi (Ε.Δ.Χ.) invitations, their routes and prices, outcomes known so far (barren routes, routes with offers, barren share by school type), ΔΣΑ registry size per category, bus comparison, proposed gate N, open gaps, method with a dated correction note, sources (ΚΗΜΔΗΣ, Διαύγεια, pkm.gov.gr). `docs/plan.md` §1, §6 and §10 point here. |
| `routes-edx-2026.csv` | 156 route lines extracted from Annex I of the 1st and 2nd taxi invitations of 2026: invitation, ΑΔΑΜ, A/A, normalised route code, escort (ΝΑΙ/ΟΧΙ), daily reference price in € excl. VAT, days, 3-year budget in €, whether the same route (same code and same school) appears in both invitations. Totals match each invitation's «ΣΥΝΟΛΑ» row to the cent. Research data behind `desk-research-2026.md`, not a data contract. |
