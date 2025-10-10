-- GitHub integration storage

CREATE TABLE IF NOT EXISTS gh_connection (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    installation_id TEXT,
    account_login TEXT,
    account_id TEXT,
    encrypted_access_token TEXT,
    encrypted_refresh_token TEXT,
    token_expires_at TIMESTAMP,
    scopes TEXT,
    mock INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gh_repo (
    id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL REFERENCES gh_connection(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL UNIQUE,
    default_branch TEXT,
    private INTEGER DEFAULT 0,
    url TEXT,
    head_sha TEXT,
    last_index_at TIMESTAMP,
    languages TEXT,
    top_paths TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gh_repo_connection ON gh_repo(connection_id);

CREATE TABLE IF NOT EXISTS gh_file (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL REFERENCES gh_repo(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    sha TEXT,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    snippet TEXT NOT NULL,
    embedding_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gh_file_repo ON gh_file(repo_id);
CREATE INDEX IF NOT EXISTS idx_gh_file_repo_path ON gh_file(repo_id, path);

CREATE TABLE IF NOT EXISTS gh_issue_pr (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL REFERENCES gh_repo(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    state TEXT,
    updated_at TIMESTAMP,
    url TEXT,
    snippet TEXT,
    embedding_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repo_id, number, type)
);

CREATE INDEX IF NOT EXISTS idx_gh_issue_repo ON gh_issue_pr(repo_id);
CREATE INDEX IF NOT EXISTS idx_gh_issue_updated ON gh_issue_pr(repo_id, updated_at);

