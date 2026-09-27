export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "sending" | "sent" | "error";
}

export interface Conversation {
  id: string;
  title: string;
  date: string;
  messages: Message[];
}
