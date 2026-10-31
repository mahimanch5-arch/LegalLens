import type { LegalDocument } from '@/api/types';

/**
 * Mock workspace. Every document, party, court and case here is fictional and exists only
 * to exercise the UI. None of it is a real filing or a real authority.
 */

const daysAgo = (d: number, h = 10) => {
  const t = new Date();
  t.setDate(t.getDate() - d);
  t.setHours(h, 12, 0, 0);
  return t.toISOString();
};

export const DOC_IDS = {
  acme: 'doc_acme_msa',
  helix: 'doc_helix_saas',
  smith: 'doc_smith_v_jones',
  bayview: 'doc_bayview_v_delmar',
  reyes: 'doc_reyes_complaint',
  exhibit: 'doc_exhibit_c',
  minutes: 'doc_board_minutes',
} as const;

const PDF = 'application/pdf';
const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

export const seedDocuments: LegalDocument[] = [
  {
    id: DOC_IDS.acme,
    name: 'Acme–Northwind Master Services Agreement.pdf',
    mimeType: PDF,
    sizeBytes: 1_842_311,
    pages: 42,
    type: 'contract',
    typeConfidence: 0.97,
    typeOverridden: false,
    status: 'ready',
    progress: 100,
    lowOcrPages: [],
    uploadedAt: daysAgo(12),
  },
  {
    id: DOC_IDS.helix,
    name: 'Helix SaaS Subscription Agreement.docx',
    mimeType: DOCX,
    sizeBytes: 412_880,
    pages: 18,
    type: 'contract',
    typeConfidence: 0.94,
    typeOverridden: false,
    status: 'ready',
    progress: 100,
    lowOcrPages: [],
    uploadedAt: daysAgo(9),
  },
  {
    id: DOC_IDS.smith,
    name: 'Smith v. Jones Holdings, Inc. (9th Cir.).pdf',
    mimeType: PDF,
    sizeBytes: 988_102,
    pages: 27,
    type: 'opinion',
    typeConfidence: 0.99,
    typeOverridden: false,
    status: 'ready',
    progress: 100,
    lowOcrPages: [],
    uploadedAt: daysAgo(7),
  },
  {
    id: DOC_IDS.bayview,
    name: 'Bayview Freight Lines v. Delmar Shipping Co.pdf',
    mimeType: PDF,
    sizeBytes: 1_204_550,
    pages: 31,
    type: 'opinion',
    typeConfidence: 0.98,
    typeOverridden: false,
    status: 'ready',
    progress: 100,
    lowOcrPages: [],
    uploadedAt: daysAgo(7, 11),
  },
  {
    id: DOC_IDS.reyes,
    name: 'Complaint – Reyes v. Coastal Logistics.pdf',
    mimeType: PDF,
    sizeBytes: 702_431,
    pages: 22,
    type: 'pleading',
    typeConfidence: 0.95,
    typeOverridden: false,
    status: 'ready',
    progress: 100,
    lowOcrPages: [],
    uploadedAt: daysAgo(3),
  },
  {
    id: DOC_IDS.exhibit,
    name: 'Exhibit C – Amendment No. 2 (signed scan).pdf',
    mimeType: PDF,
    sizeBytes: 3_906_118,
    pages: 6,
    type: 'contract',
    typeConfidence: 0.71,
    typeOverridden: false,
    status: 'ready',
    progress: 100,
    lowOcrPages: [2, 4, 5],
    uploadedAt: daysAgo(2),
  },
  {
    id: DOC_IDS.minutes,
    name: 'Board Minutes 2025-Q4 (protected).pdf',
    mimeType: PDF,
    sizeBytes: 523_004,
    pages: null,
    type: 'other',
    typeConfidence: 0,
    typeOverridden: false,
    status: 'failed',
    progress: 0,
    error: 'This PDF is password-protected. Remove the password, then upload it again.',
    lowOcrPages: [],
    uploadedAt: daysAgo(1),
  },
];

/**
 * Authored page text, keyed by document id then page number. Pages that are not authored
 * get generated filler text (see pages.ts) so the viewer always has something to show.
 */
export const authoredPages: Record<string, Record<number, string>> = {
  [DOC_IDS.acme]: {
    1: `MASTER SERVICES AGREEMENT

This Master Services Agreement (the "Agreement") is entered into as of March 1, 2024 (the "Effective Date") by and between Northwind Analytics, LLC, a Delaware limited liability company ("Provider"), and Acme Industrial Holdings, Inc., an Ohio corporation ("Customer").

RECITALS

WHEREAS, Provider is in the business of providing data-engineering, analytics and managed reporting services; and

WHEREAS, Customer wishes to engage Provider to perform such services on the terms set out below;

NOW, THEREFORE, in consideration of the mutual covenants contained herein, the parties agree as follows.`,
    3: `2. TERM

2.1 Initial Term. This Agreement commences on the Effective Date and continues for an initial term of three (3) years (the "Initial Term").

2.2 Renewal. Thereafter this Agreement renews automatically for successive one (1) year periods (each a "Renewal Term") unless either party gives written notice of non-renewal at least ninety (90) days before the end of the then-current term.

2.3 Statements of Work. Each Statement of Work ("SOW") remains in effect for the period stated in it, and any SOW in effect on expiry of this Agreement continues to be governed by this Agreement until that SOW is completed or terminated.`,
    5: `3. SERVICES AND SERVICE LEVELS

3.1 Performance. Provider shall perform the services described in each SOW (the "Services") in a professional and workmanlike manner, in accordance with generally accepted industry standards.

3.2 Service Levels. Provider shall make the hosted reporting platform available at least 99.9% of each calendar month, excluding scheduled maintenance notified at least forty-eight (48) hours in advance. If availability falls below that level, Customer's sole remedy is the service credit set out in Exhibit B.

3.3 Personnel. Provider shall assign suitably qualified personnel and shall not replace the designated engagement lead without Customer's prior written consent, which shall not be unreasonably withheld.`,
    6: `4. CUSTOMER OBLIGATIONS

4.1 Cooperation. Customer shall provide Provider with timely access to the systems, data and personnel reasonably necessary for Provider to perform the Services.

4.2 Approvals. Customer shall review and approve or reject each deliverable within ten (10) business days of delivery. A deliverable not rejected in writing within that period is deemed accepted.

4.3 Customer Data. Customer is responsible for the accuracy and lawful collection of all data it provides to Provider.`,
    9: `6. FEES AND PAYMENT

6.1 Fees. Customer shall pay the fees set out in each SOW. Unless the SOW states otherwise, fees are invoiced monthly in arrears.

6.2 Payment Terms. Customer shall pay all undisputed invoices within thirty (30) days of receipt. Late amounts bear interest at the lesser of 1.0% per month or the maximum rate permitted by law.

6.3 Disputed Amounts. Customer shall notify Provider of any disputed amount in writing before the payment due date, and the parties shall work in good faith to resolve the dispute within thirty (30) days.

6.4 Fee Increases. Provider may increase its rates no more than once in any twelve (12) month period, and by no more than five percent (5%), on sixty (60) days' written notice.`,
    14: `11. TERMINATION

11.1 Termination for Convenience. Either party may terminate this Agreement for convenience upon one hundred twenty (120) days' prior written notice to the other party.

11.2 Termination for Cause. Either party may terminate this Agreement upon written notice if the other party materially breaches this Agreement and fails to cure such breach within thirty (30) days after receiving written notice describing the breach in reasonable detail.

11.3 Insolvency. Either party may terminate this Agreement immediately upon written notice if the other party becomes insolvent, makes a general assignment for the benefit of creditors, or becomes the subject of any bankruptcy proceeding that is not dismissed within sixty (60) days.`,
    15: `11.4 Effect of Termination. Upon any termination, Customer shall pay Provider for all Services performed through the effective date of termination, and each party shall return or destroy the other party's Confidential Information within fifteen (15) days.

11.5 Transition Assistance. On Customer's written request made before the effective date of termination, Provider shall provide reasonable transition assistance for up to ninety (90) days at its then-current rates.

11.6 Survival. Sections 6 (Fees and Payment), 9 (Confidentiality), 13 (Limitation of Liability), 14 (Indemnification) and 16 (General) survive any termination or expiry of this Agreement.`,
    18: `13. LIMITATION OF LIABILITY

13.1 Cap. EXCEPT FOR BREACHES OF SECTION 9 (CONFIDENTIALITY) AND A PARTY'S INDEMNIFICATION OBLIGATIONS, IN NO EVENT SHALL EITHER PARTY'S AGGREGATE LIABILITY ARISING OUT OF THIS AGREEMENT EXCEED THE FEES PAID OR PAYABLE BY CUSTOMER IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO THE CLAIM.

13.2 Exclusion of Damages. NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL OR PUNITIVE DAMAGES, OR FOR LOST PROFITS, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

13.3 Application. The limitations in this Section 13 apply to all causes of action in aggregate, whether in contract, tort or otherwise.`,
    19: `14. INDEMNIFICATION

14.1 By Provider. Provider shall defend Customer against any third-party claim alleging that the Services or deliverables infringe any United States patent, copyright or trademark, and shall pay any damages finally awarded or agreed in settlement.

14.2 By Customer. Customer shall defend Provider against any third-party claim arising from Customer Data or from Customer's use of the deliverables in violation of applicable law.

14.3 Procedure. The indemnified party shall give prompt written notice of the claim, allow the indemnifying party sole control of the defense, and provide reasonable cooperation at the indemnifying party's expense.`,
    22: `16. GENERAL

16.1 Notices. All notices under this Agreement must be in writing and delivered by hand, by recognized overnight courier, or by email to the addresses set out in the signature block, with a copy by courier for any notice of breach or termination.

16.2 Assignment. Neither party may assign or transfer this Agreement, in whole or in part, without the prior written consent of the other party, except that either party may assign this Agreement without consent to a successor in connection with a merger, acquisition, or sale of all or substantially all of its assets, provided the successor assumes this Agreement in writing. Any change of control of Provider shall be deemed an assignment for purposes of this Section 16.2, and Customer may terminate this Agreement within sixty (60) days after receiving notice of such change of control.`,
    23: `16.3 Independent Contractors. The parties are independent contractors, and nothing in this Agreement creates a partnership, joint venture or agency relationship.

16.4 Entire Agreement. This Agreement, together with all SOWs and exhibits, is the entire agreement between the parties and supersedes all prior agreements on its subject matter.

16.5 Governing Law. This Agreement is governed by the laws of the State of Delaware, without regard to its conflict-of-laws principles. Any dispute shall be resolved exclusively in the state or federal courts located in Wilmington, Delaware.`,
  },

  [DOC_IDS.helix]: {
    1: `SAAS SUBSCRIPTION AGREEMENT

This SaaS Subscription Agreement is made on January 15, 2025 between Helix Cloud Software, Inc. ("Helix") and Acme Industrial Holdings, Inc. ("Subscriber").

Helix grants Subscriber a non-exclusive, non-transferable right to access and use the Helix Contract Insights platform during the Subscription Term, solely for Subscriber's internal business purposes.`,
    4: `3. SUBSCRIPTION TERM AND RENEWAL

3.1 The Subscription Term begins on the Order Start Date and continues for twelve (12) months.

3.2 The Subscription Term renews automatically for successive twelve (12) month periods unless either party notifies the other of non-renewal at least sixty (60) days before the end of the current term.

3.3 Helix may increase subscription fees on renewal by giving written notice at least seventy-five (75) days before the renewal date.`,
    7: `6. DATA PROTECTION

6.1 Helix shall process Subscriber Data only on Subscriber's documented instructions and in accordance with the Data Processing Addendum.

6.2 Helix shall notify Subscriber without undue delay, and in any event within seventy-two (72) hours, after becoming aware of a Security Incident affecting Subscriber Data.

6.3 On termination, Helix shall make Subscriber Data available for export for thirty (30) days and shall then delete it.`,
    11: `9. LIMITATION OF LIABILITY

9.1 Each party's total liability under this Agreement shall not exceed two times (2x) the fees paid by Subscriber in the twelve (12) months before the claim.

9.2 The cap in Section 9.1 does not apply to Helix's data-protection obligations under Section 6, for which Helix's liability is capped at five times (5x) such fees.`,
  },

  [DOC_IDS.smith]: {
    1: `UNITED STATES COURT OF APPEALS
FOR THE NINTH CIRCUIT

DANIEL SMITH, Plaintiff-Appellee,
v.
JONES HOLDINGS, INC., Defendant-Appellant.

Appeal from the United States District Court for the Northern District of California.

Before: Circuit Judges PARK, OKAFOR and ALVAREZ.

Opinion by Judge Okafor; Dissent by Judge Alvarez.

We consider whether an email can satisfy a contract's requirement of "written notice" of breach. The district court held that it can, and entered judgment for Smith. We AFFIRM.`,
    3: `I. BACKGROUND

Smith supplied warehouse-automation software to Jones Holdings under a 2019 license agreement. Section 12 of the agreement permitted either party to terminate for material breach after giving "written notice" and a thirty-day opportunity to cure. The agreement designated a contact person and an email address for each party but did not specify any method of delivering notices.

On June 3, 2021, Smith's general counsel emailed Jones Holdings' designated contact, identifying four unpaid invoices by number and amount and stating that Smith would terminate if they were not paid within thirty days. Jones Holdings did not pay, and Smith terminated on July 6, 2021.`,
    8: `II. ISSUE PRESENTED

The sole question on appeal is whether an email sent to a party's designated contact satisfies a contractual requirement of "written notice" where the contract does not prescribe a method of delivery.

Jones Holdings argues that "written notice" in a commercial agreement carries a settled meaning requiring a signed paper document delivered by mail or courier. Smith responds that the term requires only a writing that conveys the required information to the other party.`,
    12: `III. DISCUSSION

We hold that, absent language in the contract requiring a specific method of delivery, an email that identifies the breach with reasonable particularity and is sent to the contractually designated contact constitutes written notice.

The purpose of a notice-and-cure provision is to inform the breaching party of the default and give it a fair opportunity to remedy it. An email to the designated contact that names the invoices, the amounts and the deadline serves that purpose as fully as a letter would.`,
    14: `Jones Holdings' reliance on custom is unpersuasive. Where sophisticated parties intended to require a particular form of delivery, they said so elsewhere in the same agreement: Section 18 requires that any notice of an intellectual-property claim be sent "by certified mail, return receipt requested." The absence of comparable language in Section 12 indicates that the parties did not intend to impose one there.

Nor did Jones Holdings suffer any prejudice. Its designated contact acknowledged receipt of the June 3 email the following day and forwarded it to the company's accounts-payable team.`,
    26: `IV. CONCLUSION

Because Smith's June 3, 2021 email gave Jones Holdings written notice of the breach and a thirty-day opportunity to cure, Smith's termination was effective. The judgment of the district court is AFFIRMED.`,
    27: `ALVAREZ, Circuit Judge, dissenting:

I respectfully dissent. The majority's rule makes the sufficiency of notice turn on after-the-fact inquiries into whether an email was read and by whom. Parties who draft notice provisions are entitled to the certainty that formal delivery provides, and I would hold that "written notice," without more, requires a signed writing delivered by a recognized physical method.`,
  },

  [DOC_IDS.bayview]: {
    1: `UNITED STATES DISTRICT COURT
SOUTHERN DISTRICT OF NEW YORK

BAYVIEW FREIGHT LINES, INC., Plaintiff,
v.
DELMAR SHIPPING CO., Defendant.

OPINION AND ORDER

Bayview Freight Lines moves for partial summary judgment declaring that the limitation-of-liability clause in its 2020 carriage agreement with Delmar Shipping does not bar its claim for losses caused by Delmar's alleged gross negligence. For the reasons below, the motion is GRANTED IN PART and DENIED IN PART.`,
    2: `PROCEDURAL HISTORY

Bayview filed this action asserting claims for breach of contract and negligence after a cargo of refrigerated pharmaceuticals spoiled while in Delmar's custody. Following discovery, Bayview moved for partial summary judgment on the enforceability of Section 9 of the carriage agreement, which caps Delmar's liability at the freight charges paid for the affected shipment.`,
    10: `DISCUSSION

A limitation-of-liability clause negotiated between sophisticated commercial parties is enforceable according to its terms, but does not shield a party from liability for its own gross negligence.

The record shows that Delmar's crew disabled the refrigeration alarm on the affected container for eleven hours. Whether that conduct rises to gross negligence is a question of fact for the jury, which precludes summary judgment on that issue.`,
    30: `CONCLUSION

Bayview's motion is GRANTED to the extent it seeks a declaration that Section 9 does not limit damages caused by gross negligence, and DENIED to the extent it asks the Court to find gross negligence as a matter of law. The parties shall submit a joint pretrial order within forty-five days.`,
  },

  [DOC_IDS.reyes]: {
    1: `SUPERIOR COURT OF THE STATE OF CALIFORNIA
FOR THE COUNTY OF LOS ANGELES

MARIA REYES, an individual, Plaintiff,
v.
COASTAL LOGISTICS, INC., a California corporation; and DOES 1 through 20, Defendants.

COMPLAINT FOR DAMAGES

1. Wrongful termination in violation of public policy;
2. Retaliation in violation of Labor Code section 1102.5;

DEMAND FOR JURY TRIAL`,
    4: `FACTUAL ALLEGATIONS

12. Plaintiff was employed by Defendant as a dispatch supervisor from April 2019 until her termination on February 14, 2025.

13. On January 6, 2025, Plaintiff reported to Defendant's regional operations manager, in writing, that drivers were being instructed to falsify hours-of-service logs.

14. On January 21, 2025, Plaintiff repeated her report to Defendant's human-resources department and requested an investigation.

15. Less than four weeks later, Defendant terminated Plaintiff's employment, citing "restructuring." No other dispatch supervisor was terminated.`,
    9: `FIRST CAUSE OF ACTION
(Wrongful Termination in Violation of Public Policy — Against All Defendants)

24. Plaintiff's reports concerned the falsification of records required by state and federal transportation-safety regulations, which reflect fundamental public policies of the State of California.

25. Plaintiff's reports were a substantial motivating reason for Defendant's decision to terminate her employment.`,
    11: `SECOND CAUSE OF ACTION
(Retaliation in Violation of Labor Code Section 1102.5 — Against All Defendants)

31. Plaintiff disclosed information she had reasonable cause to believe disclosed a violation of a state or federal statute or regulation to a person with authority over her.

32. Defendant retaliated against Plaintiff for those disclosures by terminating her employment.`,
    21: `PRAYER FOR RELIEF

WHEREFORE, Plaintiff prays for judgment against Defendants as follows:

1. For compensatory damages, including lost wages and benefits, in an amount to be proven at trial;
2. For emotional-distress damages;
3. For punitive damages;
4. For civil penalties under Labor Code section 1102.5(f);
5. For reasonable attorneys' fees and costs;
6. For such other relief as the Court deems just and proper.`,
  },

  [DOC_IDS.exhibit]: {
    1: `AMENDMENT NO. 2 TO MASTER SERVICES AGREEMENT

This Amendment No. 2 is made effective September 1, 2025 between Northwind Analytics, LLC ("Provider") and Acme Industrial Holdings, Inc. ("Customer") and amends the Master Services Agreement dated March 1, 2024.

1. Section 6.4 of the Agreement is deleted and replaced with the following: "Provider may increase its rates no more than once in any twelve (12) month period, and by no more than three percent (3%), on ninety (90) days' written notice."`,
    2: `2. The Initial Term is ext3nded to f0ur (4) years fr0m the Effect1ve Date. [illegible stamp] ... C0ntract0r sha11 ...`,
  },
};
