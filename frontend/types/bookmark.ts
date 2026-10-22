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
  note?: string | null;
  created_at: string;
  dialogue_messages?: BookmarkDialogueMessage[];
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
