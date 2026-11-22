export interface BookmarkDialogueMessage {
  sender_type: "USER" | "AGENT_TUTOR" | string;
  content: string;
  attachment_url?: string | null;
  created_at?: string | null;
}

export interface BookmarkItem {
  id: string;
  student_id: string;
  session_id: string;
  session_title?: string | null;
  problem_snapshot?: string | null;
  attachment_url?: string | null;
  chat_summary?: string | null;
  independence_score?: number | null;
  title?: string | null;
  note?: string | null;
  playlist_ids?: string[];
  created_at: string;
  dialogue_messages?: BookmarkDialogueMessage[];
}

export interface PlaylistOption {
  id: string;
  name: string;
  description?: string | null;
  color?: string | null;
  is_default?: boolean;
  item_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface BookmarkCreatePayload {
  session_id: string;
  note?: string;
}

export interface BookmarkFilterState {
  searchQuery: string;
  scoreFilter: "all" | "perfect" | "passed";
  hasAttachmentOnly: boolean;
}
