CREATE TABLE research_conversations (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE research_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES research_conversations(id),
    role VARCHAR(32) NOT NULL,
    message_type VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    job_id UUID,
    created_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE research_jobs
    ADD COLUMN conversation_id UUID REFERENCES research_conversations(id),
    ADD COLUMN trigger_message_id UUID REFERENCES research_messages(id);

ALTER TABLE research_messages
    ADD CONSTRAINT fk_research_messages_job
    FOREIGN KEY (job_id) REFERENCES research_jobs(id);

CREATE INDEX idx_research_conversations_status ON research_conversations(status);
CREATE INDEX idx_research_messages_conversation_id_created_at ON research_messages(conversation_id, created_at);
CREATE INDEX idx_research_jobs_conversation_id ON research_jobs(conversation_id);
