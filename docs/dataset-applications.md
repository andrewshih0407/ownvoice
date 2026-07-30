# Dataset licence applications — ready to send

**You must sign and send these yourself.** Each requires accepting a legal
agreement and supplying your own identity and affiliation; an application signed
by anyone else is invalid. Everything below is filled in except the bracketed
fields.

Fill these once, reuse everywhere:

```
[FULL NAME]        Andrew Shih
[EMAIL]            andrewshih0407@gmail.com
[AFFILIATION]      <school / lab / "independent researcher">
[SUPERVISOR]       <name + email, if you have one — materially improves odds>
[COUNTRY]          <country of residence>
```

Priority order: **1 → 2 → 3 → 4**. Send 1 and 2 today; approval lag is weeks and
the build phase starts mid-September.

---

## 1. MDSC / AISHELL-6B — Mandarin (highest priority)

17 h, 21 dysarthric + 25 control speakers, home-environment recordings, **with
intelligibility ratings**. Mandarin, so it directly serves the Taiwan case.

- Page: https://www.aishelltech.com/AISHELL_6B
- Paper: [arXiv 2406.10304](https://arxiv.org/abs/2406.10304) (Interspeech 2024)
- Holder: Beijing Hillshell Technology (北京希尔贝壳科技有限公司)
- Status: described as open-source, but the product page carries no download
  link. Requires a direct request.

**Draft email** — to the contact address on the AISHELL site (and cc the paper's
corresponding author):

> Subject: Request for access — MDSC / AISHELL-6B Mandarin dysarthria corpus
>
> Dear AISHELL team,
>
> I am [FULL NAME], [AFFILIATION]. I am requesting access to the Mandarin
> Dysarthria Speech Corpus (MDSC / AISHELL-6B), described in "Enhancing Voice
> Wake-Up for Dysarthria" (Interspeech 2024, arXiv 2406.10304).
>
> I am developing a speech-restoration system for Mandarin speakers with
> dysarthria, with a focus on tone recovery — Mandarin tone is lexically
> contrastive, and existing dysarthria research is overwhelmingly English-first,
> so tonal-language degradation is under-studied. The work is a non-commercial
> research entry for Taiwan's 2026 Presidential Hackathon International Track
> (theme: Digital Inclusion in the AI Era).
>
> I would use the corpus solely for non-commercial research, would not
> redistribute it, and would cite the corpus paper in any resulting write-up. I
> am happy to sign whatever licence agreement you require and to provide
> institutional confirmation.
>
> Could you advise on the access procedure?
>
> With thanks,
> [FULL NAME] · [EMAIL] · [AFFILIATION]

---

## 2. CUDYS — Cantonese (best scientific fit for the tone claim)

10+ h, 27 impaired speakers, Chinese University of Hong Kong. Built specifically
to study speaking rate, pitch and loudness control in a **tonal** language.

**Why this may matter more than Mandarin data:** Cantonese has six tones. It is
the only *real patient* corpus identified so far that can test the tone-
destruction hypothesis at all — EasyCall (Italian) cannot, because Italian is not
tonal. A positive result on Cantonese would make the tonal argument evidence-based
rather than theoretical, and cross-lingual tonal transfer is itself a publishable
contribution.

- Origin paper: [Development of a Cantonese dysarthric speech corpus](https://www.isca-archive.org/interspeech_2015/wong15_interspeech.html) (Interspeech 2015)
- Follow-up: [Recent Progress in the CUHK Dysarthric Speech Recognition System](https://arxiv.org/pdf/2201.05845)
- Holder: Human-Computer Communications Laboratory, Dept. of Systems Engineering
  & Engineering Management, CUHK
- Status: no public download. Contact the CUHK group directly — get current
  addresses from the corresponding authors of the 2022 paper above.

**Draft email:**

> Subject: Access request — CUDYS Cantonese dysarthric speech corpus
>
> Dear Professor [NAME],
>
> I am [FULL NAME], [AFFILIATION]. I am writing to request access to the CUDYS
> Cantonese dysarthric speech corpus described in Wong et al., Interspeech 2015,
> and extended in your later dysarthric ASR work.
>
> I am building a speech-restoration system for dysarthric speakers of tonal
> languages. My central hypothesis is that tonal languages present a failure mode
> absent from the English dysarthria literature: because tone is lexically
> contrastive, a mistoned reconstruction yields a different word rather than an
> accented one. I have implemented a segmental tone error rate (tone errors
> measured only on syllables recognized correctly at the segmental level) to
> isolate this effect, and validated on simulated data that prosodic flattening
> degrades tone-scale F0 variance monotonically. CUDYS would let me test this on
> authentic patient speech in a tonal language.
>
> The work is non-commercial research, submitted to Taiwan's 2026 Presidential
> Hackathon International Track. I will not redistribute the data, will use it
> only for research, and will cite the corpus papers. I am glad to sign your
> licence agreement and provide institutional verification.
>
> Would you be able to advise on the access procedure?
>
> With thanks,
> [FULL NAME] · [EMAIL] · [AFFILIATION]

---

## 3. CDSD — Mandarin, largest Chinese dysarthria corpus

133 h, 44 speakers. MELab, Institute of Psychology, Chinese Academy of Sciences.

This one has a **defined procedure**, no email improvisation needed:

1. Download the licence agreement:
   http://melab.psych.ac.cn/License_Agreement_CDSD.pdf
2. Complete and sign it.
3. Submit via the application link on http://melab.psych.ac.cn/CDSD.html

Paper: [arXiv 2310.15930](https://arxiv.org/abs/2310.15930) (Interspeech 2024)

Research-purpose text to paste into the form:

> Non-commercial research on speech restoration for Mandarin speakers with
> dysarthria, focusing on tone recovery. Tone in Mandarin is lexically
> contrastive, so tonal errors change word identity; existing dysarthria research
> is predominantly English-language and does not address this. Data will be used
> solely for research, will not be redistributed, and the corpus will be cited.

**Note the optics**, worth a moment's thought: CDSD and MDSC are both
PRC-institution datasets, and this is a Taiwanese presidential competition. Not a
blocker, and MDSC is the better fit anyway, but consider a sentence of framing in
the submission if a PRC corpus ends up central.

---

## 4. DysArinVox — Mandarin, includes continuous speech

Mandarin dysphonia **and** dysarthria. Explicitly built because existing dysphonia
databases over-emphasize sustained vowels and lack continuous speech — consonants,
phoneme variation, and coarticulation. That makes it a better match for
sentence-level restoration than isolated-word corpora.

- Paper: [DysArinVox (Interspeech 2024)](https://www.isca-archive.org/interspeech_2024/zhang24l_interspeech.html)
  · [PDF](https://www.isca-archive.org/interspeech_2024/zhang24l_interspeech.pdf)
- Authors: Haojie Zhang, Tao Zhang, Ganjun Liu, Dehui Fu, Xiaohui Hou, Ying Lv
- Status: no distribution mechanism published. Read the PDF for the
  corresponding author's address, then adapt the email in §1.

---

## 5. English corpora — lower priority

Useful for architecture work and for the ALS/CP expansion population, not for the
Mandarin demo.

- **TORGO** — 23 h, 8 dysarthric (CP/ALS) + 7 control, includes articulatory
  measurement. Via LDC: https://catalog.ldc.upenn.edu/LDC2012S02 (membership or
  fee), or the U Toronto page.
- **UASpeech** — 102.7 h, 16 dysarthric + 13 typical, isolated words. Signed UIUC
  licence.

---

## Available immediately, no application

- **EasyCall** — `changelinglab/easycall-dysarthria`, **CC-BY-NC-2.0**, ungated.
  21,386 real dysarthric utterances, Italian isolated command words, with
  per-speaker severity labels. Loader implemented: `src/data_real.py`.
  Answers "does this work on real dysarthria at all"; cannot test tone (Italian
  is not tonal) and is not continuous speech.

## Never use

The TORGO re-uploads on HuggingFace (`Ankesh1234/dysarthria-torgo`,
`resproj007/torgo_dysarthric_*`, `charleslwang/torgo-dysarthric`, and similar)
carry **no declared licence**. They are LDC-restricted patient medical data
redistributed without authorization. Beyond the ethics, the competition handbook
makes improper acquisition or use of personal data an explicit **disqualification**
criterion — using them would put the whole submission at risk.
