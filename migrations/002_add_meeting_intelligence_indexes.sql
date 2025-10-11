-- Migration: 002_add_meeting_intelligence_indexes.sql
-- Description: Additional indexes for Meeting Intelligence performance
-- Date: 2025-10-08

-- Composite indexes for common query patterns
CREATE INDEX idx_meeting_org_started ON meeting(org_id, started_at DESC);
CREATE INDEX idx_transcript_meeting_time ON transcript_segment(meeting_id, ts_start_ms);
CREATE INDEX idx_action_item_meeting_status ON action_item(meeting_id, status);

-- JSONB indexes for efficient queries on structured data
CREATE INDEX idx_meeting_participants_gin ON meeting USING gin(participants);
CREATE INDEX idx_summary_bullets_gin ON meeting_summary USING gin(bullets);
CREATE INDEX idx_summary_decisions_gin ON meeting_summary USING gin(decisions);
CREATE INDEX idx_summary_risks_gin ON meeting_summary USING gin(risks);

-- Partial indexes for performance on common filters
CREATE INDEX idx_meeting_recent ON meeting(started_at DESC) 
    WHERE started_at > now() - interval '30 days';

CREATE INDEX idx_action_item_open ON action_item(meeting_id, created_at DESC) 
    WHERE status = 'open';

CREATE INDEX idx_summary_completed ON meeting_summary(meeting_id) 
    WHERE processing_status = 'completed';

-- Index for hybrid search (text + metadata)
CREATE INDEX idx_meeting_search_composite ON meeting(org_id, started_at DESC, provider)
    WHERE ended_at IS NOT NULL;
