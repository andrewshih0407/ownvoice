# OwnVoice

Restoring intelligible speech to people with dysarthria — **in their own voice**.

Entry for the 2026 Presidential Hackathon International Track
(Theme: *Digital Inclusion in the AI Era*).

## The pitch

Pre-operative voice banking and post-operative voice restoration for Taiwan's
betel-nut oral cancer patients, expanding to stroke and Parkinson's dysarthria.

Speech-to-speech conversion takes unintelligible dysarthric speech and
re-synthesizes it as clear speech using a clone of the speaker's own banked
voice. Real-time mode for phone calls; API mode so any voice assistant becomes
usable.

## Why Taiwan

- Oral cancer is the **4th most common cancer and 4th leading cause of cancer
  death among Taiwanese men**; male incidence ~29.8/100k, ~10x the female rate.
  86% of incidence variance is explained by betel nut consumption.
- Head/neck cancer surgery is **scheduled**, so the voice can be banked
  pre-operatively — this solves the hardest problem in voice cloning
  (stroke gives no warning; surgery does).
- Affected population skews toward laborers, drivers, and Indigenous
  communities — an underserved group, tying the project to the inclusion theme.
- Stroke: ~210/100k person-years incidence; dysarthria follows ~26% of
  ischemic strokes.
- Parkinson's: age-standardized prevalence +394% (2000-2021); Taiwan became a
  super-aged society in 2025.

## Technical contribution

Dysarthria research is overwhelmingly English-first. Mandarin tone carries
lexical meaning and requires precisely the rapid lingual/laryngeal control that
dysarthria destroys — so a mistoned reconstruction produces *a different word*,
not an accented one. Solving this for Mandarin (and Taiwanese Hokkien, which has
more tones) is a contribution that transfers to every tonal-language country.

## ⚠ Competition timeline — read before building

Verified against the official 2026 handbook (`docs/handbook-2026.pdf`).

| Phase | Date | What's required |
|---|---|---|
| **Submission closes** | **July 31, 2026, 17:00 GMT+8** | Online form. **Written proposal — no prototype required** |
| Preliminary review | Aug 6-16 | Feasibility 40% / Innovation 30% / Social Impact 30% |
| Results | Late August | |
| Mentorship | Mid-Sept to mid-Oct | Free 1-on-1 AI consulting, tech consultants, **field validation support** |
| **Final review** | **Late October** | Adds Implementation & Verification 30%; **system demo or code walkthrough required** |
| Awards | Early-mid December | |

**The model is built for late October, not July 31.** The preliminary is scored
on the written proposal alone. Organizers provide mentorship and field-validation
support during the build phase.

## ⚠ Eligibility blockers

1. **Team size: 3-10 members.** Solo entries are ineligible.
2. **At least one member must hold non-ROC (Taiwan) nationality.**
3. Two members designated primary/secondary contact.
4. All materials in English.
5. Original work; if previously sold or awarded elsewhere, requires >=50%
   modification.

## Repo layout

```
data/    # datasets (gitignored — most are license-restricted)
docs/    # handbook, dataset access tracking, proposal drafts
src/     # pipeline code
```

See `docs/datasets.md` for dataset access status — **the license applications
are the critical path and should be filed immediately**, since approval lag is
measured in weeks and the build phase starts in September.
