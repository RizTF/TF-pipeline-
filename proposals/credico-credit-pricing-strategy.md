# CREDICO — ADVERTISING CREDIT PRICING STRATEGY (INTERNAL)

**Prepared for:** Riz
**Re:** Alicia Harris / Credico — volume job-advertising deal (~800 credits/year)
**Date:** 8 June 2026
**Status:** Internal working doc — NOT for client. Pricing floors based on supplier cost cards.

---

## 1. THE DECISION: BUNDLED PER-CREDIT, NOT PER-BOARD

**Recommendation: sell ONE blended "TF advertising credit", volume-tiered. Deliver each
advert on whichever board is cheapest/best (Reed-led). Never itemise by board.**

The supplier cost cards make this decision for us — the three boards have incompatible
economics, and two of them break the deal if Credico ever sees them line-itemed:

| Board | Pricing model | Cost/credit @ 800 | Sold per-board would be |
|-------|---------------|-------------------|-------------------------|
| **Reed** | Per-credit | **£19.19** | £25–29 — beats Credico's current rate ✅ |
| **Premium board (Tier A)** | Per-credit | **£35.00** | £45–52 — *above* their current £34.38 ❌ |
| **Indeed** | Spend / CPC × 1.30 | budget-based | does not map to "credits" ❌ |

**Credico's current rate: £34.38/credit** (£275 ÷ 8 standard credits).

- Reed is the cost-leader but only at volume: £49.52/credit @ 50 → £19.19 @ 500+.
- The premium board's *cost* (£35) is already above what Credico pay today — uncompetitive
  as a standalone line. Keep it as fill-insurance, used selectively.
- Indeed is spend-based — usually the highest-volume source for field-sales/agent roles,
  but it cannot be expressed as a "credit."

Bundling lets us: (a) hide the per-board spread (our media-buying margin), (b) deliver on
Reed by default and dip into the premium board / Indeed only when fill requires it,
(c) re-optimise or swap suppliers behind the scenes without renegotiating with Credico,
(d) match exactly what Alicia asked for — "tiered options, volume-based saving."

This is normal media-buying arbitrage against a defined deliverable (one managed live
advert) — no gharar, no deception.

---

## 2. RECOMMENDED TIER LADDER (CLIENT-FACING)

Our cost base literally proves the "more credits = greater saving" promise: at low volume
Reed costs more than Credico's current rate; at 800 we can beat it comfortably. Lean into it.

| Tier | Annual credits | **Sell £/credit** | vs current £34.38 | Margin if Reed-delivered |
|------|----------------|-------------------|-------------------|--------------------------|
| Standard | up to 100 | £34 | hold | protects vs Reed's high low-volume cost |
| Growth | 101–300 | £32 | −7% | cost £24.41 → ~24% |
| Scale | 301–500 | £29 | −16% | cost £19.19 → ~34% |
| **Partner (Credico)** | 500–800 committed | **£29** | **−16%** | cost £19.19 → £9.81 = **34%** |

Headline number to put in front of Alicia: **£29/credit on an annual 800 commitment.**

---

## 3. THE WINNING NARRATIVE FOR ALICIA

| | Calculation | Annual |
|---|---|---|
| Credico today (Totaljobs equivalent) | 800 × £34.38 | **£27,504** |
| **TF Partner offer** | 800 × £29 | **£23,200** |
| **Credico saves** | | **£4,304 (16%)** |

And our side of it:

| Delivery mix | Cost/credit | Profit/credit @ £29 | Total profit @ 800 |
|--------------|-------------|---------------------|--------------------|
| Pure Reed | £19.19 | £9.81 | **£7,848** |
| 75% Reed / 25% premium board | £23.14 | £5.86 | £4,688 |
| 85% Reed / 15% premium board | £21.56 | £7.44 | £5,952 |

Credico saves money, we make £5–8k on the ads alone, and the filtering add-on stacks on top.
That is the case for moving them off Totaljobs.

---

## 4. THREE FLAGS BEFORE SENDING

1. **500 = 800 same Reed unit cost (£19.19).** Reed gives no extra break for the jump to
   800, so don't price the 800 tier far below 500 — we'd be discounting margin we aren't
   getting. **Push Reed for a genuine 800-volume rate first**; if they give it, we keep the
   upside.
2. **Never itemise the premium board (£35–45) or Indeed CPC to Credico.** One blended credit
   price only. The spread is the margin.
3. **Offer Indeed as an optional "Performance Surge" line** — managed at cost + 30% — for
   campaign launches needing fast volume. Keeps the core credit price Reed-anchored and
   competitive while giving Alicia a turbo button. (Indeed economics: spend × 1.30, e.g.
   £2,000 budget → £2,600 to client → £600 GP.)

---

## 5. AI APPLICANT FILTERING — THE ADD-ON (PRICED SEPARATELY)

### What it is (from the live TF-Pipeline engine)
The same engine currently filtering Paul's inbound email replies is, architecturally, an
AI inbound-application filtering pipeline:

1. **Ingest** — every application hits a webhook and queues automatically (24/7).
2. **Score/classify** — Claude reads each application against the role spec and sorts it
   (qualified / borderline / reject) with a confidence score, in seconds.
3. **Act** — qualified → acknowledge + shortlist; borderline → flag for human review;
   reject → polite auto-response; spam/auto-replies → binned.
4. **Notify + log** — strong matches pushed to the hiring manager with a one-line summary;
   every applicant written to a live dashboard (Google Sheet).
5. **Thread memory** — keeps history per applicant so follow-ups stay in context.

### Why it sells to Credico
Field-sales/agent adverts generate huge, low-quality applicant floods. 800 credits could
mean 10,000+ applications. The engine screens, scores and shortlists at near-zero marginal
cost (Claude API ≈ pennies per application), saving their recruiters dozens of hours/week
and giving applicants a fast, professional response (employer-brand win).

### Pricing
- **Recommended: +£8/credit add-on** — "every applicant screened, scored and shortlisted."
  At 800 credits = **£6,400/yr, ~95% margin.** Stays in the per-credit language Credico
  already think in → easy yes.
- **Alternative:** flat managed-screening retainer (~£500–750/month) — better recurring
  revenue, decoupled from credit count, but a bigger separate line for procurement.

Lead with the per-credit add-on.

---

## 6. ONE-LINE SUMMARY

Sell a single blended credit at **£29 on an 800 annual commitment** (16% below Credico's
current rate, 34% margin on Reed), keep board allocation and the premium/Indeed costs behind
the curtain, offer Indeed as an optional surge boost, and stack **AI Applicant Filtering at
+£8/credit** on top. Credico save money; we make £12–14k/year across ads + filtering.
