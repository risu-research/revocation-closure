# Court-order clause ledger

This file records the **entered court orders** used to design the synthetic policy checks. The underlying PDFs are docket documents mirrored by Justia. Verify the entered text against the original docket when applying an order in a real matter. Page labels below are the printed pages in each protective order.

## Acosta v. The New York Times Company
S.D.N.Y., No. 1:25-cv-01119, Dkt. 39, entered September 19, 2025. [PDF](https://cases.justia.com/federal/district-courts/new-york/nysdce/1%3A2025cv01119/636556/39/0.pdf).

- Paragraph **14(c)(ii)**, printed p. 15, requires return, sequestration or destruction within **ten days** of the producing party's written notice, covering the protected document, copies, notes, abstracts and compilations. The receiving party must extract copies of the protected document from a litigation-review database under its control.
- Paragraph **14(d)**, p. 15, requires sequestration until resolution when the protected information has already been used in or described in other generated or retained documents. It also addresses reasonable steps to recover previously disclosed materials.
- Paragraph **14(f)**, p. 15, limits use absent the court's order.
- The clock is a disposition obligation; it is not permission for continued use until that date. The test focuses on producer notice, not the separately described receiving-party discovery in paragraph 14(b).

**Tests:** historical output remains blocked after notice; clean independent work stays available; database extraction is recognized as a distinct obligation.

## NECEC Transmission LLC v. Campos EPC, LLC
S.D.N.Y., No. 1:25-cv-05351, Dkt. 58, entered November 18, 2025. [PDF](https://cases.justia.com/federal/district-courts/new-york/nysdce/1%3A2025cv05351/644926/58/0.pdf).

- Section **IV.1(b)**, printed pp. 17–18, requires return, sequestration or destruction of protected material and copies within **two business days** following emailed written notice. Use and disclosure remain restricted pending resolution or withdrawal, subject to the order's limited court-challenge exception.
- The same provision requires reasonable recall after earlier disclosure and counsel's written certification upon the producing party's request.
- Destruction of summaries, notes, extracts or derivative data follows a **different temporal condition**. It applies immediately if no challenge is made or upon a court ruling in the producing party's favor after challenge.
- Under **III.6(b)**, printed p. 16, qualifying backup media may remain in place, subject to the order's ongoing restrictions.

**Tests:** pending challenge defers a final derived-destruction decision; no challenge or a favorable court decision triggers the corresponding action; normal clean work remains available. A claim's withdrawal is modeled as a verified event; the system does not infer the legal result from a cached checkpoint.

## 218 Broadway, LLC v. J.P. Morgan Chase Bank, N.A.
S.D.N.Y., No. 1:25-cv-07386, Dkt. 37, entered June 8, 2026. [PDF](https://cases.justia.com/federal/district-courts/new-york/nysdce/1%3A2025cv07386/648886/37/0.pdf).

- Paragraph **16**, printed p. 12, bars submitting discovery material to public/open AI models. For a proprietary or closed AI model, receiving parties must first ensure the described non-training, confidentiality, access and deletion safeguards.

**Tests:** public tools are rejected; a closed-tool fixture is permitted only when the manually supplied assurance flags meet the selected conditions; missing assurances yield an unresolved decision. This is not a determination about any real provider.

## Spheres Music, LLC v. John Murphy
C.D. Cal., No. 2:25-cv-12197, Dkt. 34, court-entered protective order. The filed PDF retains **[PROPOSED]** on its template footers. [PDF](https://cases.justia.com/federal/district-courts/california/cacdce/2%3A2025cv12197/1000608/34/0.pdf).

- Section **12.4(b)–(c)**, printed pp. 20–21, restricts sending protected material to externally hosted AI services unless the specified enforceable contract terms cover training, purpose restriction, third-party handling, safeguards and request-based deletion of protected content and derived inputs/outputs.
- Section **12.4(d)**, p. 21, excludes free, public, personal and consumer-tier services even if they offer purported protections.
- Section **12.4(e)**, p. 21, requires written documentation of the qualifying protections and suspends the challenged tool's use for the designating party's protected material during a qualification challenge.

**Tests:** public/consumer service exclusion; a fully asserted synthetic contract; missing safeguards; challenged tool suspension; provider deletion requires independent execution evidence beyond a contractual promise or unilateral report.

## What the tests support

The legal information is extracted **manually**, and the test oracle is authored separately from the interpreter. The experiment isolates policy-enforcement behavior in a constructed LangGraph workflow with synthetic source labels and a local SQL effect store. It supports a conditional enforcement claim, not an automated legal reading or a general compliance certification. No real party notice, clock or court decision is simulated as having occurred.

The tests distinguish a court's *obligation* to dispose or sequester from an engineered *pre-effect gate* that blocks unwanted new writes. The latter is a technical safeguard inferred for the test and is not quoted as a mandated implementation in the orders.
