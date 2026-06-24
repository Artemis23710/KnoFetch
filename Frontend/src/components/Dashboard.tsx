import React, { useEffect, useState, useRef } from 'react';
import { Sidebar } from './Sidebar';
import { ChatHeader } from './ChatHeader';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { MessageSkeleton } from './Skeletons';
import type { Message, ChatSession } from '../types';
import { api } from '../lib/api';

// --- Mock Data ---
const MOCK_SESSIONS: ChatSession[] = [
{
  id: '1',
  title: 'Q3 Financial Analysis',
  updatedAt: new Date(Date.now() - 1000 * 60 * 5)
},
{
  id: '2',
  title: 'API Documentation Search',
  updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 2)
},
{
  id: '3',
  title: 'Employee Onboarding Policy',
  updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24)
}];

const INITIAL_MESSAGES: Message[] = [
{
  id: 'm1',
  role: 'ai',
  content: 'Welcome to KnoFetch! You can ask questions about your uploaded documents here. Use the **Index Documents** card in the sidebar to upload PDF documents to start indexing them.',
  timestamp: new Date()
}];

export function Dashboard() {
  // Layout State
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  // Chat State
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [documents, setDocuments] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Streamlit features migrated to React state
  const [runRagas, setRunRagas] = useState(false);
  const [ragasHistory, setRagasHistory] = useState<any[]>([]);

  // Clean up any stale override key from localStorage on launch
  useEffect(() => {
    localStorage.removeItem('nexus_api_key');
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth'
    });
  }, [messages, isGenerating]);

  // Handle responsive layout on mount/resize & Load Documents
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setIsSidebarOpen(false);
      }
    };
    handleResize(); // Initial check
    window.addEventListener('resize', handleResize);
    
    // Fetch uploaded documents on mount
    const fetchDocs = async () => {
      try {
        const docs = await api.getDocuments();
        setDocuments(docs);
      } catch (err) {
        console.error('Failed to load documents on startup:', err);
      }
    };
    fetchDocs();

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleFileUpload = async (files: FileList) => {
    if (files.length === 0 || isUploading) return;
    setIsUploading(true);
    
    const tempId = 'upload-' + Date.now();
    const uploadingMsg: Message = {
      id: tempId,
      role: 'ai',
      content: `⚙️ **System:** Processing and indexing the uploaded PDF(s)... Please wait.`,
      timestamp: new Date()
    };
    setMessages((prev) => [...prev, uploadingMsg]);

    try {
      const response = await api.uploadFiles(files);
      
      // Update documents state
      const docs = await api.getDocuments();
      setDocuments(docs);

      // Update UI with success status
      setMessages((prev) => 
        prev.map(msg => msg.id === tempId ? {
          ...msg,
          content: `✅ **System:** Successfully processed and indexed **${response.files.join(', ')}** into ChromaDB (${response.chunks_created} semantic chunks created).`
        } : msg)
      );
    } catch (err: any) {
      console.error(err);
      setMessages((prev) => 
        prev.map(msg => msg.id === tempId ? {
          ...msg,
          content: `❌ **System Error:** Failed to process document. Details: ${err.message || 'Unknown error'}`
        } : msg)
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleResetDatabase = async () => {
    if (!window.confirm("Are you sure you want to clear the entire RAG database? This will delete all indexed documents.")) {
      return;
    }
    setIsResetting(true);
    try {
      await api.resetDatabase();
      setDocuments([]);
      setRagasHistory([]);
      setMessages([{
        id: 'reset-' + Date.now(),
        role: 'ai',
        content: `🗑️ **System:** The RAG vector database has been successfully reset. All documents have been cleared.`,
        timestamp: new Date()
      }]);
    } catch (err: any) {
      alert(`Error resetting database: ${err.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isGenerating) return;
    const userText = input.trim();
    const newUserMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userText,
      timestamp: new Date()
    };
    setMessages((prev) => [...prev, newUserMsg]);
    setInput('');
    setIsGenerating(true);

    try {
      const response = await api.askQuestion(userText, undefined, runRagas);
      let content = response.answer;
      
      if (response.sources && response.sources.length > 0) {
        const uniqueSourcesMap: { [key: string]: boolean } = {};
        const citationLinks: string[] = [];
        response.sources.forEach(src => {
          const key = `${src.doc_name}-page-${src.page_number}`;
          if (!uniqueSourcesMap[key]) {
            uniqueSourcesMap[key] = true;
            citationLinks.push(`📄 **${src.doc_name}** (Page ${src.page_number})`);
          }
        });
        if (citationLinks.length > 0) {
          content += `\n\n---\n**Sources:**\n` + citationLinks.map(link => `- ${link}`).join('\n');
        }
      }

      // If RAGAS was calculated, record history
      if (response.ragas) {
        setRagasHistory(prev => [...prev, {
          question: userText,
          eval: response.ragas
        }]);
      }

      const newAiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content,
        timestamp: new Date(),
        ragas: response.ragas || null
      };
      setMessages((prev) => [...prev, newAiMsg]);
    } catch (err: any) {
      console.error(err);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: `❌ **Error:** Failed to connect to RAG server or generate response. Please ensure the backend server is running.\n\n*Details: ${err.message || 'Unknown connection error'}*`,
        timestamp: new Date()
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownloadHistory = () => {
    if (messages.length <= 1) {
      alert("No conversation history to download yet.");
      return;
    }
    const headers = ["ID", "Role", "Content", "Timestamp"];
    const rows = messages.map(msg => [
      msg.id,
      msg.role,
      `"${msg.content.replace(/"/g, '""')}"`,
      msg.timestamp instanceof Date ? msg.timestamp.toISOString() : new Date(msg.timestamp).toISOString()
    ]);
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "conversation_history.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadRagas = () => {
    if (ragasHistory.length === 0) {
      alert("No RAGAS scores to download yet.");
      return;
    }
    const headers = ["Question", "Faithfulness", "Answer Relevance", "Context Precision", "Overall Score"];
    const rows = ragasHistory.map(item => [
      `"${item.question.replace(/"/g, '""')}"`,
      item.eval.faithfulness,
      item.eval.answer_relevance,
      item.eval.context_precision,
      item.eval.overall_score
    ]);
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "ragas_scores.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleNewChat = () => {
    setMessages(INITIAL_MESSAGES);
    setInput('');
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-950 text-zinc-100 font-sans selection:bg-indigo-500/30">
      <Sidebar
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        sessions={MOCK_SESSIONS}
        activeSessionId="1"
        documents={documents}
        onResetDatabase={handleResetDatabase}
        isResetting={isResetting}
        runRagas={runRagas}
        setRunRagas={setRunRagas}
        onFileUpload={handleFileUpload}
        isUploading={isUploading}
        onDownloadHistory={handleDownloadHistory}
        onDownloadRagas={handleDownloadRagas}
        hasRagasHistory={ragasHistory.length > 0}
        onNewChat={handleNewChat} />
      

      <main className="relative flex min-w-0 flex-1 flex-col">
        <ChatHeader title="KnoFetch Assistant" />

        <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-zinc-800">
          <div className="flex flex-col pb-4">
            {messages.map((msg) =>
            <MessageBubble
              key={msg.id}
              message={msg} />

            )}
            {isGenerating && <MessageSkeleton />}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        <div className="shrink-0 bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent pt-4">
          <ChatInput
            input={input}
            setInput={setInput}
            onSubmit={handleSend}
            isLoading={isGenerating}
            onFileUpload={handleFileUpload}
            isUploading={isUploading} />
          
        </div>
      </main>
    </div>);

}