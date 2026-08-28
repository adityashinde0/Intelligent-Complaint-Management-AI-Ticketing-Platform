CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID,
    role VARCHAR(50),
    email VARCHAR(255) UNIQUE,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS complaints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    conversation_id UUID,
    raw_text TEXT,
    normalized_text TEXT,
    language VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES categories(id),
    name VARCHAR(255),
    description TEXT
);

CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY REFERENCES users(id),
    team_id UUID REFERENCES teams(id),
    availability_status VARCHAR(50),
    capacity INTEGER,
    current_load INTEGER,
    language_codes VARCHAR(255),
    skills JSONB
);

CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id UUID UNIQUE REFERENCES complaints(id),
    category_id UUID REFERENCES categories(id),
    severity VARCHAR(50),
    status VARCHAR(50),
    team_id UUID REFERENCES teams(id),
    assigned_agent_id UUID REFERENCES agents(id),
    sla_due_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    version BIGINT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES tickets(id),
    event_type VARCHAR(100),
    actor_type VARCHAR(50),
    actor_id UUID,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID REFERENCES tickets(id),
    decision_type VARCHAR(100),
    model_name VARCHAR(255),
    model_version VARCHAR(255),
    policy_version VARCHAR(255),
    confidence DOUBLE PRECISION,
    output JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_uri VARCHAR(1024),
    title VARCHAR(255),
    authority_level VARCHAR(50),
    version BIGINT,
    checksum VARCHAR(255),
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES knowledge_documents(id),
    chunk_index INTEGER,
    content TEXT,
    content_hash VARCHAR(255),
    embedding_model VARCHAR(255),
    embedding_version VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS ai_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ai_decision_id UUID REFERENCES ai_decisions(id),
    knowledge_chunk_id UUID REFERENCES knowledge_chunks(id),
    similarity_score DOUBLE PRECISION,
    rank INTEGER,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id UUID,
    action VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id UUID,
    before JSONB,
    after JSONB,
    request_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tickets_tenant_status_sev ON tickets(status, severity);
CREATE INDEX IF NOT EXISTS idx_tickets_team_status_sla ON tickets(team_id, status, sla_due_at);
CREATE INDEX IF NOT EXISTS idx_tickets_agent_status ON tickets(assigned_agent_id, status);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket_created ON ticket_events(ticket_id, created_at);
