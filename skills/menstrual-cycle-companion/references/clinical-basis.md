# Clinical & research basis

This is the knowledge the AI assistant should draw on when explaining
predictions or giving advice through this skill. It is not exhaustive
medical literature — it's the working assumptions behind the prediction math,
plus well-supported self-care measures, so advice stays grounded rather than
invented on the spot. Always pair advice with the standing disclaimer:
**this is general information, not a diagnosis, and it doesn't replace a
clinician who knows the person's history.**

## Why prediction counts backward from ovulation, not forward from day 1

The classic "28-day cycle, ovulation on day 14" model treats both halves of
the cycle as fixed. The research doesn't support that:

- The follicular phase (period start → ovulation) is the variable part of
  the cycle. Its length changes cycle to cycle and shortens somewhat with
  age.
- The luteal phase (ovulation → next period) is comparatively more
  consistent within an individual, though it is *not* a fixed 14 days — a
  2024 within-individual study (Henry et al., *Human Reproduction*) found luteal
  lengths still varied, and a large real-world dataset from the Natural
  Cycles app (600,000+ cycles) put the average luteal phase around 12-13
  days with a fairly wide normal range (roughly 10-16 days). A luteal phase
  under 10 days is considered short and is common even in otherwise regular
  cyclers.
- Practical takeaway: predicting the *next period* from cycle-length history
  and then counting *backward* by the luteal length to estimate ovulation is
  more defensible than assuming ovulation always falls on day 14. This is
  what `predict.py` does. If someone has their own tracked luteal length
  (from BBT or LH strips), use it instead of the 14-day default via the
  `bootstrap_luteal_length` field — it's a real, personal number worth
  overriding the population default with.

## Why predictions are ranges, not single dates

Within-person cycle-length variability of a few days is normal even in
people with "regular" cycles. Presenting a single date invites false
confidence. When talking about predictions, say things like "expected
around the 24th, could reasonably be a few days either side" rather than
asserting a specific day. Confidence should visibly drop for profiles with
few logged cycles or a wide spread between recent cycle lengths.

## Fertile window

Standard clinical guidance (consistent across ACOG and other patient-facing
medical sources) estimates the fertile window as roughly five days before
ovulation through one day after, reflecting sperm survival of up to ~5 days
and egg viability of about 24 hours. This is the window `predict.py`
computes. Always caveat it as a calendar estimate, not a verified
ovulation-tracking method (e.g. not as reliable as LH testing or BBT), and
never present it as a reliable contraceptive method — false confidence here
has real consequences.

## Managing period pain (dysmenorrhea)

Primary dysmenorrhea (cramping not caused by an underlying condition like
endometriosis or fibroids) affects most menstruating people at some point.
Reasonably well-supported approaches, roughly in order of evidence
strength:

- **NSAIDs** (ibuprofen, naproxen) are first-line and work by reducing
  prostaglandins, which drive the cramping. They work best started a day or
  so before bleeding begins (or at the first sign of pain) and taken on a
  regular schedule for the first 2-3 days, rather than only once pain is
  already severe.
- **Heat therapy** (heating pad/patch on the lower abdomen) has good
  evidence behind it, including recent systematic reviews showing
  meaningful pain reduction, and is essentially risk-free.
- **Exercise**, done regularly (not necessarily during the worst of the
  pain), is supported by meta-analyses for reducing dysmenorrhea intensity,
  though it works more as a preventive/ongoing habit than an acute fix.
- **Magnesium supplementation** has supportive evidence (systematic reviews
  suggest a real, modest effect) but works better as an adjunct alongside
  NSAIDs/heat than as a standalone fix, and there's no well-established
  standard dose.
- Combining an antispasmodic with an NSAID has shown better results than an
  NSAID alone in at least one RCT, worth mentioning as an option to discuss
  with a pharmacist or doctor if NSAIDs alone aren't enough.
- NSAIDs don't fully help everyone — a meaningful minority get inadequate
  relief from NSAIDs alone, which is a legitimate reason to combine
  approaches or see a doctor, not a sign something's wrong with them.

## PMS / premenstrual mood and physical symptoms

Symptom tracking itself has real value here — many people underestimate how
cyclical their mood or energy is until they see it charted, and having a log
makes it much easier to have a useful conversation with a doctor if symptoms
are significant. When giving advice: regular sleep and exercise, caffeine
and alcohol moderation, and calcium/magnesium intake all have some
supportive evidence for reducing PMS symptom severity, though none of them
work dramatically for everyone. Persistent, function-impairing mood symptoms
(possible PMDD) warrant flagging toward a clinician rather than just
self-care tips.

## When to suggest seeing a doctor (don't just hand out symptom advice)

Flag these rather than only offering self-care tips:

- Soaking through a pad/tampon every hour for several hours in a row
- Periods consistently shorter than 21 days or longer than 35 days apart
- Bleeding or spotting between periods, or after sex
- Pain that isn't meaningfully helped by NSAIDs + heat
- Sudden, significant change from someone's own normal pattern
- Missed periods with no other explanation (not just late by a few days)
- Trying to conceive for 12+ months (or 6+ months if over 35) without
  success

## Supporting a partner (for the "partner" profile role)

Useful framing for the non-menstruating partner, based on what's generally
recommended in couples/health-communication guidance: practical support
(having pain relief and a heating pad on hand, taking on a chore, checking
in without pressuring) tends to land better than unsolicited advice or
minimizing what they are feeling. Predictions are for anticipating and being
useful, not for explaining away their mood or pain in the moment — avoid
messaging that could read as "it's just hormones."
