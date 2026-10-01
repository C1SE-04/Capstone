export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "sending" | "sent" | "error";
  emotion?: "idle" | "thinking" | "suggesting" | "correct" | "incorrect" | string;
  isAnswerRevealed?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  date: string;
  messages: Message[];
}
