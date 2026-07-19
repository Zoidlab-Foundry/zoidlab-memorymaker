"""Seed 7 memory projects + 10 memory stores (owner NULL = visible to everyone),
each with sample memories, rules, and a recall test. Idempotent."""
import db_pg as db
import recall_engine


def _mem(title, content, mtype, tags, sensitivity="low", source="conversation", confidence=0.85):
    return {"title": title, "content": content, "memory_type": mtype, "tags": tags,
            "sensitivity": sensitivity, "source": source, "confidence": confidence}


def _rule(name, rtype, desc, enabled=True, condition=None, action=None):
    return {"name": name, "rule_type": rtype, "description": desc, "enabled": enabled,
            "condition_json": condition or {}, "action_json": action or {}}


REDACT_RULE = _rule("Never store secrets", "redaction",
                    "Detect and redact passwords, tokens, API keys, and SSNs before storing.",
                    condition={"contains_secret": True}, action={"redact": True, "block_if_empty": True})

# projects: (name, icon, accent, risk)
PROJECTS = [
    ("Restaurant Concierge Memory", "🍽", "#f4b860", "medium"),
    ("Legal Intake Memory", "⚖", "#818cf8", "high"),
    ("University IT Help Desk Memory", "🎓", "#4fd1c5", "medium"),
    ("Network Troubleshooting Memory", "🛰", "#22d3ee", "high"),
    ("Sales Agent Memory", "📈", "#7c5cfc", "medium"),
    ("Policy Checker Memory", "🛡", "#2dd4bf", "high"),
    ("AI Website Concierge Memory", "🌐", "#7c5cfc", "medium"),
]

# stores: (name, project, memory_type, backend, risk, description, [memories], [rules], recall_query)
STORES = [
    ("Customer Preference Memory", "Restaurant Concierge Memory", "customer_profile", "postgres_pgvector", "medium",
     "Persistent customer preferences for concierge agents.",
     [_mem("Customer prefers outdoor seating", "Customer Michael prefers outdoor patio seating and usually asks for quiet tables.", "customer_profile", ["preference", "seating"], "low"),
      _mem("Gluten-free interest", "Customer asked about gluten-free pasta options on their last two visits.", "customer_profile", ["preference", "dietary"], "low"),
      _mem("Anniversary in June", "Customer mentioned their anniversary is in June; suggest the tasting menu.", "customer_profile", ["preference", "occasion"], "medium"),
      _mem("Dislikes cilantro", "Customer noted a strong dislike of cilantro.", "customer_profile", ["preference", "dietary"], "low"),
      _mem("Prefers early reservations", "Customer usually books 6pm or earlier for dinner.", "customer_profile", ["preference", "reservation"], "low")],
     [REDACT_RULE, _rule("Remember stated preferences", "remember", "Store customer preferences when explicitly stated.")],
     "Does this customer prefer outdoor seating?"),

    ("Restaurant Knowledge Memory", "Restaurant Concierge Memory", "document", "postgres_pgvector", "low",
     "Menu facts, hours, and policies for the concierge.",
     [_mem("Sunday hours", "Evo Italian opens at 4:00 PM on Sundays for dinner service.", "document", ["hours"], "low", "document"),
      _mem("Gluten-free pasta", "The house pappardelle can be made gluten-free on request.", "document", ["menu", "dietary"], "low", "document"),
      _mem("Private events", "Private event inquiries for parties over 12 should be routed to the manager.", "document", ["events", "policy"], "low", "document"),
      _mem("Corkage policy", "Corkage is $25 per bottle, waived for members.", "document", ["policy"], "low", "document"),
      _mem("Wood-fired specialty", "The signature dish is the wood-fired margherita with San Marzano tomatoes.", "document", ["menu"], "low", "document")],
     [REDACT_RULE, _rule("Prefer document memory", "retrieval", "Prefer document-sourced facts over conversation snippets for menu questions.")],
     "What time do you open on Sunday?"),

    ("Conversation Summary Memory", "Restaurant Concierge Memory", "conversation", "mock", "low",
     "Rolling summaries of guest conversations.",
     [_mem("Booking thread — Dana", "Dana booked a table for 4 on Friday at 7pm, requested a window seat.", "conversation", ["reservation"], "low"),
      _mem("Complaint resolved", "Guest reported a cold entrée; comped dessert and noted for follow-up.", "conversation", ["service"], "medium"),
      _mem("Event inquiry", "Caller asked about a 30-person rehearsal dinner in August.", "conversation", ["events"], "low")],
     [REDACT_RULE, _rule("Summarize long chats", "summarization", "Summarize conversations after 20 messages.", condition={"messages_gt": 20})],
     "Any recent event inquiries?"),

    ("Legal Intake Fact Memory", "Legal Intake Memory", "customer_profile", "postgres_pgvector", "high",
     "Client-provided intake facts and summaries. Sensitive — not legal advice.",
     [_mem("MVA intake — date", "Prospective client reported a motor-vehicle accident on the 12th; other driver allegedly texting.", "customer_profile", ["intake", "mva"], "high", "conversation"),
      _mem("Injury note", "Client reports ongoing neck pain following the accident; seen at urgent care.", "customer_profile", ["intake", "medical"], "high", "conversation"),
      _mem("Employment matter", "Client describes a wrongful-termination concern; requested attorney review.", "customer_profile", ["intake", "employment"], "high", "conversation"),
      _mem("No advice given", "Reminder: intake only, no legal conclusions provided to the client.", "procedural", ["policy"], "medium", "system")],
     [REDACT_RULE, _rule("High-risk approval", "access", "Require human approval before storing high-risk legal memory.", condition={"sensitivity": "high"}, action={"require_approval": True})],
     "What did the client say about the accident?"),

    ("University Help Desk Knowledge Memory", "University IT Help Desk Memory", "document", "postgres_pgvector", "medium",
     "Campus IT knowledge and routing patterns.",
     [_mem("VPN requires MFA", "Campus VPN connections require MFA enrollment via Duo before the profile will connect.", "document", ["vpn", "mfa"], "low", "document"),
      _mem("Password reset", "Student password resets go through the identity portal; staff resets require a ticket.", "document", ["account"], "low", "document"),
      _mem("Wi-Fi onboarding", "Eduroam onboarding requires the university certificate; guests use the open SSID.", "document", ["wifi"], "low", "document"),
      _mem("LMS outage routing", "LMS outages are routed to the academic-tech queue, priority 2.", "procedural", ["routing"], "low", "system"),
      _mem("Common Mac VPN fix", "On macOS, reinstalling the VPN profile resolves most connection failures.", "document", ["vpn", "mac"], "low", "document")],
     [REDACT_RULE, _rule("Expire stale tickets", "expiration", "Expire troubleshooting details after 30 days.", condition={"age_days_gt": 30}, action={"expire": True})],
     "How do I connect to the campus VPN on a Mac?"),

    ("Network Incident Memory", "Network Troubleshooting Memory", "episodic", "postgres_pgvector", "high",
     "Past incidents, known fixes, and incident summaries.",
     [_mem("Uplink flaps → optics", "Switch uplink flaps often indicate an optics or patch-cable issue; check optic levels first.", "episodic", ["incident", "optics"], "medium", "system"),
      _mem("AP flaps during migration", "AP flaps during the Cisco-to-Mist migration in Building B were expected during cutover.", "episodic", ["incident", "wifi", "migration"], "medium", "system"),
      _mem("CRC errors on Gi1/0/48", "Rising CRC errors on core-sw-01 Gi1/0/48 traced to a failing SFP; replaced 3/14.", "episodic", ["incident", "crc"], "medium", "system"),
      _mem("Building B temporary note", "Temporary: Building B uplink on backup path until fiber repair completes.", "episodic", ["temporary"], "medium", "system"),
      _mem("Loop from misconfig", "A broadcast storm on VLAN 40 was caused by a missing BPDU guard on an access port.", "episodic", ["incident", "loop"], "medium", "system")],
     [REDACT_RULE, _rule("Expire temporary notes", "expiration", "Expire temporary troubleshooting details after 30 days.", condition={"tag": "temporary", "age_days_gt": 30}, action={"expire": True})],
     "Why is the switch uplink flapping with CRC errors?"),

    ("Device Context Memory", "Network Troubleshooting Memory", "organization", "postgres_pgvector", "medium",
     "Per-device notes and topology context.",
     [_mem("core-sw-01 role", "core-sw-01 is the primary distribution switch for Buildings A and B.", "organization", ["topology"], "low", "document"),
      _mem("Mist migration status", "Wireless in Buildings A–C migrated to Mist; D and E pending.", "organization", ["wifi", "status"], "low", "document"),
      _mem("Optic standard", "Standard uplink optics are 10G LR; keep 2 spares per closet.", "organization", ["standard"], "low", "document"),
      _mem("Maintenance window", "Change window is Sundays 02:00–05:00 local.", "organization", ["policy"], "low", "document")],
     [REDACT_RULE, _rule("Tenant isolation", "access", "Keep device memory scoped to the owning org/tenant.", action={"tenant_isolation": True})],
     "What optics standard do we use for uplinks?"),

    ("Sales Lead Memory", "Sales Agent Memory", "customer_profile", "postgres_pgvector", "medium",
     "Lead preferences, qualification history, and follow-up context.",
     [_mem("Acme Fintech — budget", "Acme Fintech VP of Eng has budget approved for a Q3 pilot.", "customer_profile", ["lead", "budget"], "medium", "conversation"),
      _mem("Prefers async demos", "Lead prefers a recorded demo before a live call.", "customer_profile", ["lead", "preference"], "low", "conversation"),
      _mem("Competitor eval", "Lead is also evaluating a competitor; differentiate on governance.", "customer_profile", ["lead", "competitive"], "medium", "conversation"),
      _mem("Follow-up cadence", "Agreed to a follow-up in 2 weeks after internal review.", "customer_profile", ["lead", "followup"], "low", "conversation")],
     [REDACT_RULE, _rule("Remember qualification", "remember", "Store budget/authority/need/timeline signals for each lead.")],
     "Does this lead have budget for a pilot?"),

    ("AI Policy Memory", "Policy Checker Memory", "semantic", "postgres_pgvector", "high",
     "Company AI usage policies and data-classification rules.",
     [_mem("No PCI to external models", "Policy: payment-card data (PCI) must never be sent to external model providers.", "semantic", ["policy", "pci"], "high", "document"),
      _mem("PII requires redaction", "Policy: PII must be redacted before storage or external model calls.", "semantic", ["policy", "pii"], "high", "document"),
      _mem("Approved models", "Only Nyquest-routed and approved provider models may be used for production.", "semantic", ["policy", "models"], "medium", "document"),
      _mem("Right to be forgotten", "Users may request deletion of their memories; honor within 30 days.", "semantic", ["policy", "rtbf"], "high", "document"),
      _mem("High-risk approval", "High-risk data usage requires human approval before proceeding.", "procedural", ["policy", "approval"], "high", "document")],
     [REDACT_RULE, _rule("Block secrets", "redaction", "Block storage of any credentials or PCI data outright.", action={"block": True})],
     "Can we send customer card numbers to an external model?"),

    ("Website FAQ Memory", "AI Website Concierge Memory", "document", "postgres_pgvector", "medium",
     "Business facts, FAQs, and service descriptions for the site concierge.",
     [_mem("Free trial", "We offer a 14-day Pro trial with no credit card required.", "document", ["faq", "trial"], "low", "document"),
      _mem("Pricing tiers", "Plans are Free, Pro, and Teams; Teams adds SSO and shared workspaces.", "document", ["faq", "pricing"], "low", "document"),
      _mem("Support hours", "Support is available 9–6 ET on business days; Pro gets priority.", "document", ["faq", "support"], "low", "document"),
      _mem("Data residency", "Enterprise data residency options are available on Teams.", "document", ["faq", "enterprise"], "medium", "document"),
      _mem("Cancellation", "Plans can be cancelled anytime; access continues to the end of the billing period.", "document", ["faq", "billing"], "low", "document")],
     [REDACT_RULE, _rule("Prefer official FAQ", "retrieval", "Prefer FAQ document memory over visitor-supplied claims.")],
     "Do you offer a free trial?"),
]


def run():
    db.init()
    if db.list_projects():
        return 0
    pmap = {}
    for (name, icon, accent, risk) in PROJECTS:
        pmap[name] = db.create_project({"name": name, "description": f"Memory project: {name}.",
                                        "icon": icon, "accent": accent, "risk_level": risk}, owner=None)
    made = 0
    for (name, proj, mtype, backend, risk, desc, mems, rules, query) in STORES:
        store = db.create_store({
            "name": name, "project_id": pmap[proj]["id"], "description": desc, "memory_type": mtype,
            "storage_backend": backend, "risk_level": risk, "status": "active",
            "governance": {"risk_level": risk, "pii_risk": "high" if risk == "high" else "low",
                           "sensitive_data": risk == "high", "requires_human_approval": risk == "high"},
        }, owner=None)
        for m in mems:
            db.create_entry(store["id"], m, owner=None, source=m.get("source", "conversation"))
        for r in rules:
            db.create_rule(store["id"], r)
        # seed a recall test so the store shows a recall score
        entries = db.list_entries(store["id"])
        res = recall_engine.recall(db.get_store_raw(store["id"]), entries, query, top_k=5, threshold=0.3)
        db.log_recall(store["id"], {"query": query, "context": {}, "retrieval_mode": "hybrid", "top_k": 5,
                                    "threshold": 0.3, "retrieved_entries": res["retrieved"],
                                    "assembled_context": res["assembled_context"], "score": res["recall_quality_score"],
                                    "latency_ms": res["latency_ms"]}, owner=None)
        made += 1
    return made
