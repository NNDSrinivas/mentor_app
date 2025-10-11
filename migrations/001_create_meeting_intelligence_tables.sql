-- Migration: 001_create_meeting_intelligence_tables.sql
-- Description: Create tables for Meeting Intelligence feature
-- Date: 2025-10-08

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Meeting table: Core meeting metadata
CREATE TABLE meeting (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID UNIQUE NOT NULL,
    title TEXT,
    provider TEXT, -- 'google_meet', 'zoom', 'teams', etc.
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    participants JSONB DEFAULT '[]',
    org_id UUID,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for faster session lookups
CREATE INDEX idx_meeting_session_id ON meeting(session_id);
CREATE INDEX idx_meeting_org_id ON meeting(org_id);
CREATE INDEX idx_meeting_started_at ON meeting(started_at);

-- Transcript segment table: Individual speaker segments
CREATE TABLE transcript_segment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES meeting(id) ON DELETE CASCADE,
    ts_start_ms INTEGER NOT NULL,
    ts_end_ms INTEGER NOT NULL,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    confidence NUMERIC(5,4), -- Speech recognition confidence
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for efficient querying
CREATE INDEX idx_transcript_meeting_id ON transcript_segment(meeting_id);
CREATE INDEX idx_transcript_speaker ON transcript_segment(speaker);
CREATE INDEX idx_transcript_timestamp ON transcript_segment(ts_start_ms);

-- Meeting summary table: AI-generated meeting summaries
CREATE TABLE meeting_summary (
    meeting_id UUID PRIMARY KEY REFERENCES meeting(id) ON DELETE CASCADE,
    bullets JSONB NOT NULL DEFAULT '[]', -- Array of summary bullet points
    decisions JSONB NOT NULL DEFAULT '[]', -- Array of firm decisions made
    risks JSONB NOT NULL DEFAULT '[]', -- Array of identified risks
    processing_status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT, -- Store any processing errors
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Action item table: Extracted actionable items
CREATE TABLE action_item (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES meeting(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    assignee TEXT, -- Can be null if no specific assignee
    due_hint TEXT, -- Natural language due date hint
    confidence NUMERIC(5,4) NOT NULL, -- AI confidence in extraction
    source_segment UUID REFERENCES transcript_segment(id),
    status TEXT DEFAULT 'open', -- 'open', 'in_progress', 'completed', 'cancelled'
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for action item queries
CREATE INDEX idx_action_item_meeting_id ON action_item(meeting_id);
CREATE INDEX idx_action_item_assignee ON action_item(assignee);
CREATE INDEX idx_action_item_status ON action_item(status);
CREATE INDEX idx_action_item_confidence ON action_item(confidence DESC);

-- Trigger to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_meeting_updated_at BEFORE UPDATE ON meeting
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meeting_summary_updated_at BEFORE UPDATE ON meeting_summary
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_action_item_updated_at BEFORE UPDATE ON action_item
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for full-text search
CREATE INDEX idx_transcript_text_search ON transcript_segment USING gin(to_tsvector('english', text));
CREATE INDEX idx_meeting_title_search ON meeting USING gin(to_tsvector('english', coalesce(title, '')));
