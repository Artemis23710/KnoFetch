export type Role = 'user' | 'ai';

export interface Message {
  id: string;
  role: Role;
  content: string;
  timestamp: Date;
  ragas?: any;
}

export interface ChatSession {
  id: string;
  title: string;
  updatedAt: Date;
}