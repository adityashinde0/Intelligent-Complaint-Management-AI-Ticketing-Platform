from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

class InMemoryDatabase:
    """Authoritative System of Record maintaining full relational integrity as defined in schema.sql."""
    
    def __init__(self):
        self.users: Dict[UUID, Dict[str, Any]] = {}
        self.complaints: Dict[UUID, Dict[str, Any]] = {}
        self.categories: Dict[UUID, Dict[str, Any]] = {}
        self.teams: Dict[UUID, Dict[str, Any]] = {}
        self.agents: Dict[UUID, Dict[str, Any]] = {}
        self.tickets: Dict[UUID, Dict[str, Any]] = {}
        self.ticket_events: List[Dict[str, Any]] = []
        self.ai_decisions: Dict[UUID, Dict[str, Any]] = {}
        self.ai_evidence: List[Dict[str, Any]] = []
        self.knowledge_documents: Dict[UUID, Dict[str, Any]] = {}
        self.knowledge_chunks: Dict[UUID, Dict[str, Any]] = {}
        self.audit_logs: List[Dict[str, Any]] = []
        self.outbox: List[Dict[str, Any]] = []
        self.conversations: Dict[UUID, Dict[str, Any]] = {}
        self.messages: List[Dict[str, Any]] = []
        self.idempotency_records: Dict[str, Any] = {}
        self._seed_initial_data()

    def _seed_initial_data(self):
        # 1. Tenants & Teams
        tenant_id = UUID("11111111-1111-1111-1111-111111111111")
        
        team_network_id = UUID("22222222-2222-2222-2222-222222222201")
        team_billing_id = UUID("22222222-2222-2222-2222-222222222202")
        team_hardware_id = UUID("22222222-2222-2222-2222-222222222203")
        team_tier2_id = UUID("22222222-2222-2222-2222-222222222204")
        team_overflow_id = UUID("22222222-2222-2222-2222-222222222205")

        self.teams[team_network_id] = {"id": team_network_id, "name": "Network & Infrastructure"}
        self.teams[team_billing_id] = {"id": team_billing_id, "name": "Billing & Account Operations"}
        self.teams[team_hardware_id] = {"id": team_hardware_id, "name": "Hardware & Equipment"}
        self.teams[team_tier2_id] = {"id": team_tier2_id, "name": "Tier-2 Escalations"}
        self.teams[team_overflow_id] = {"id": team_overflow_id, "name": "Overflow"}

        # 2. Categories
        cat_network_id = UUID("33333333-3333-3333-3333-333333333301")
        cat_billing_id = UUID("33333333-3333-3333-3333-333333333302")
        cat_hardware_id = UUID("33333333-3333-3333-3333-333333333303")
        cat_security_id = UUID("33333333-3333-3333-3333-333333333304")
        cat_general_id = UUID("33333333-3333-3333-3333-333333333305")

        self.categories[cat_network_id] = {
            "id": cat_network_id, "parent_id": None, "name": "Network Outage",
            "description": "Broadband, fiber, cellular signal drop, routing failures"
        }
        self.categories[cat_billing_id] = {
            "id": cat_billing_id, "parent_id": None, "name": "Billing Discrepancy",
            "description": "Overcharges, refunds, unrecognized invoice items"
        }
        self.categories[cat_hardware_id] = {
            "id": cat_hardware_id, "parent_id": None, "name": "Hardware Malfunction",
            "description": "Router light blinking red, modem failure, power adapter defective"
        }
        self.categories[cat_security_id] = {
            "id": cat_security_id, "parent_id": None, "name": "Account Security",
            "description": "Unauthorized access, data breach, credentials compromised"
        }
        self.categories[cat_general_id] = {
            "id": cat_general_id, "parent_id": None, "name": "General Inquiry",
            "description": "Plan upgrades, operating hours, terms and policies"
        }

        # 3. Users & Agents
        cust_user_id = UUID("44444444-4444-4444-4444-444444444401")
        agent_user1_id = UUID("44444444-4444-4444-4444-444444444402")
        agent_user2_id = UUID("44444444-4444-4444-4444-444444444403")
        admin_user_id = UUID("44444444-4444-4444-4444-444444444404")

        now = datetime.now(timezone.utc)
        self.users[cust_user_id] = {
            "id": cust_user_id, "tenant_id": tenant_id, "role": "customer",
            "email": "customer@enterprise.com", "password": "password123", "status": "ACTIVE", "created_at": now
        }
        self.users[agent_user1_id] = {
            "id": agent_user1_id, "tenant_id": tenant_id, "role": "agent",
            "email": "sarah.agent@enterprise.com", "password": "password123", "status": "ACTIVE", "created_at": now
        }
        self.users[agent_user2_id] = {
            "id": agent_user2_id, "tenant_id": tenant_id, "role": "agent",
            "email": "alex.agent@enterprise.com", "password": "password123", "status": "ACTIVE", "created_at": now
        }
        self.users[admin_user_id] = {
            "id": admin_user_id, "tenant_id": tenant_id, "role": "admin",
            "email": "admin@enterprise.com", "password": "password123", "status": "ACTIVE", "created_at": now
        }

        # Agent profiles
        self.agents[agent_user1_id] = {
            "id": agent_user1_id,
            "name": "Sarah Chen",
            "team_id": team_network_id,
            "availability_status": "AVAILABLE",
            "capacity": 10,
            "current_load": 2,
            "language_codes": "en,es",
            "skills": ["network", "outage", "fiber", "routing"]
        }
        self.agents[agent_user2_id] = {
            "id": agent_user2_id,
            "name": "Alex Kumar",
            "team_id": team_billing_id,
            "availability_status": "AVAILABLE",
            "capacity": 12,
            "current_load": 4,
            "language_codes": "en,hi",
            "skills": ["billing", "refunds", "invoicing", "contracts"]
        }

        # 4. Knowledge Base Documents & Chunks
        doc1_id = UUID("55555555-5555-5555-5555-555555555501")
        doc2_id = UUID("55555555-5555-5555-5555-555555555502")
        
        self.knowledge_documents[doc1_id] = {
            "id": doc1_id,
            "source_uri": "kb://network/fiber-router-restart",
            "title": "Standard Router Reset & Gateway Diagnostics",
            "authority_level": "approved",
            "version": 3,
            "checksum": "sha256-doc1",
            "status": "ACTIVE",
            "created_at": now
        }
        self.knowledge_documents[doc2_id] = {
            "id": doc2_id,
            "source_uri": "kb://billing/refund-policy",
            "title": "Disputed Charges and Enterprise Refund SLA",
            "authority_level": "approved",
            "version": 2,
            "checksum": "sha256-doc2",
            "status": "ACTIVE",
            "created_at": now
        }

        chunk1_id = UUID("66666666-6666-6666-6666-666666666601")
        chunk2_id = UUID("66666666-6666-6666-6666-666666666602")

        self.knowledge_chunks[chunk1_id] = {
            "id": chunk1_id,
            "document_id": doc1_id,
            "document_title": "Standard Router Reset & Gateway Diagnostics",
            "chunk_index": 0,
            "content": "To perform a router power-cycle: Unplug the AC power adapter for 30 seconds. Reconnect and wait 3 minutes until the optical WAN light turns solid green. If the PON light remains red or blinking, an optical fiber cut has occurred requiring an on-site technician ticket.",
            "content_hash": "hash-chunk1",
            "embedding_model": "text-embedding-004-v1",
            "embedding_version": "v1.0"
        }
        self.knowledge_chunks[chunk2_id] = {
            "id": chunk2_id,
            "document_id": doc2_id,
            "document_title": "Disputed Charges and Enterprise Refund SLA",
            "chunk_index": 0,
            "content": "Customers disputing recurring line items or service unavailability adjustments may request invoice credits within 60 days of statement issuance. Disputed amounts under $100 are credited automatically within 2 business days. Amounts above $100 require billing supervisor review and ticket issuance.",
            "content_hash": "hash-chunk2",
            "embedding_model": "text-embedding-004-v1",
            "embedding_version": "v1.0"
        }

db = InMemoryDatabase()
