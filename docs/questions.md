### 1. Night Audit "Blocker" Resolution
- **Question:** The prompt states Night Audit "blocks closure" if folios are out of balance by >$0.01. How should the system handle a deadlock where an agent cannot find the error immediately?
- **My Understanding:** In hospitality, you cannot "stop time." There must be a way to move the business day forward.
- **Solution:** Implement a "Suspense/Adjustment Account." Discrepancies are posted to a system-generated adjustment line item with a mandatory "Force Close" reason, allowing the audit to complete while flagging the folio for management review.

### 2. Credit Score Calculation (300–850)
- **Question:** How do 1–5 star ratings and "violations" mathematically translate into the 300–850 range?
- **My Understanding:** A standard weighted formula is needed to prevent volatile swings.
- **Solution:** Use the formula: 
  $$Score = 700 + (\text{Avg Rating} - 3) \times 30 - (\text{Violations} \times 50)$$
  The score is capped at 850 and floored at 300.

### 3. Pricing Race Condition (10-Minute Window)
- **Question:** How is the "10-minute re-confirm" window enforced when pricing changes?
- **My Understanding:** The system needs to track the version of the price at the moment the guest adds it to the cart.
- **Solution:** Each cart item will store a `price_version_id` and `timestamp`. Upon submission, if the current `price_version_id` differs, the backend returns a `409 Conflict`. The client then enters a "Locked Re-confirm" state for 600 seconds.

### 4. Printing to Local Printers via Docker
- **Question:** How does a containerized web-app "print to local printers" without internet/cloud print?
- **My Understanding:** Standard hardware integration in Docker is complex. 
- **Solution:** The system will generate PDF blobs using `ReportLab` or `WeasyPrint` for the browser to handle via the local OS print spooler, ensuring compatibility with thermal and laser printers.

### 5. Split/Merge Order Logic
- **Question:** When an order is split by "supplier" or "warehouse," does it become two separate financial entities?
- **My Understanding:** For tracking SLAs, they must be distinct yet linked.
- **Solution:** Implement a `ParentOrder` -> `SubOrder` relationship. The Folio tracks the `ParentOrder` total, while the Service Staff interface tracks individual `SubOrder` states.
