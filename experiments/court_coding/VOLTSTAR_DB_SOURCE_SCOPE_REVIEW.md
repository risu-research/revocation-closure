# Voltstar database-deletion coding review

**Cell:** `21-DB`  
**Entered order:** *Voltstar Technologies, Inc. v. Amazon.com, Inc.*, No. 1:25-cv-01791-JMF, Doc. 35 (S.D.N.Y., May 30, 2025)  
**Original coding:** 1  
**Sealed second-pass coding:** 0  
**Adjudicated coding:** 0

## Coding rule

The frozen [codebook](codebook.csv) assigns `DB` to a named database, e-room, litigation-support system or similarly specific storage target. General electronic-copy obligations alone fall below this threshold. The source-specific analysis asks whether an entered order expressly directs deletion or removal from the identified system in connection with protected-material recovery.

## Source check

[Voltstar entered order, Doc. 35, 35-page PDF](https://cases.justia.com/federal/district-courts/new-york/nysdce/1%3A2025cv01791/637904/35/0.pdf)

| Clause | What the order requires | DB assessment |
| --- | --- | --- |
| §2.14 | Defines professional vendors, including services that organize, store and retrieve data | A definition of eligible service providers |
| §3 | Extends protection to copies, extracts and summaries | Scope of material |
| §11, PDF pp. 21–22 | On privilege notice, return the material or confirm reasonable steps to permanently delete electronic copies from electronic records | General electronic-copy deletion; no named storage target |
| §13.5, PDF pp. 23–25 | Supplies a stand-alone source-code review computer and an inspection room, with approved viewing and storage tools | Access and inspection controls; no instruction to clear a named review system after clawback |
| §§13.9–13.12 | Restricts copying and transfer from the computer; removes notes and physical materials from the review room after an inspection session | Source-code copying and room housekeeping |
| §§13.13–13.16 | Controls paper copies, deposition printouts and authorized electronic copies; requires logs of certain copies | Copy and custody controls; no named-system deletion duty |
| §15, PDF p. 32 | Requires return or destruction of protected material at final disposition with an archival exception | General disposition across protected material |

The wording in §13.11 about removing items from the Source Code Review Room addresses the physical inspection room after each session. Its duty is separate from deleting records in a document-review database or electronic discovery room.

## Positive comparison

[Fayles v. Ford Motor Co., No. 1:25-cv-10161-FDS, Doc. 19, §16(c), PDF p. 8](https://cases.justia.com/federal/district-courts/massachusetts/madce/1%3A2025cv10161/279944/19/0.pdf) expressly directs deletion from systems housing identified privileged materials and explicitly names document review databases and e-rooms. That provision meets the same `DB` rule and is coded 1 in the corpus.

## Review method and result

The researcher checked the entered Voltstar order's full searchable text and the surrounding language of §§2–3, 11, 13 and 15, including rendered source pages available from the public PDF. Searches covered `database`, `review database`, `e-room`, `data room`, `repository`, `system`, `erase`, `purge`, `delete`, `remove`, `destroy`, `electronic records`, `review room`, and `computer`. All potentially relevant clauses were read in context. The signed entered filing and its docket identity were also cross-checked against the public docket listing.

**Finding:** Retain `21-DB=0`. The entered order specifies electronic-copy deletion and controlled source-code inspection, with no express database/e-room-specific deletion duty found. The direct comparison with §16(c) of Fayles supports the narrower coding rule.

**Review status:** Completed researcher-conducted, document-wide searchable-text and clause-context assessment, with targeted PDF-page visual checks. No independent second-reader coding or complete 35-page page-image-by-page-image negative certification was conducted. This is a documented source-coding judgment, not proof that every possible interpretation has been eliminated.

This supplement preserves the [earlier five-cell source-review snapshot](SOURCE_REVIEW_5_2026-11-20.csv). It changes no coding values or frequency counts.
