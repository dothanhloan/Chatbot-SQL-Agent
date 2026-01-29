import { useState, useEffect, useRef } from "react";
import "./App.css";

const API_URL = `${import.meta.env.VITE_API_BASE}/chat`;



interface Message {
  role: "user" | "bot";
  text: string;
  timestamp: Date;
}

const suggestedQuestions = [
  "Giới thiệu về VietGuard",
  "AI SOC là gì?",
  "Chính sách bảo mật",
  "Dịch vụ của ICS",
];

export default function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const chatBoxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const messageText = text || question;
    if (!messageText.trim()) return;

    const newUserMessage: Message = {
      role: "user",
      text: messageText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setQuestion("");
    setLoading(true);
    setIsTyping(true);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: messageText }),
      });

      const data = await res.json();

      // Simulate typing delay for better UX
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: "bot", text: data.answer, timestamp: new Date() },
        ]);
        setIsTyping(false);
      }, 800);
    } catch (err) {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: "bot", text: "❌ Lỗi kết nối backend. Vui lòng thử lại sau.", timestamp: new Date() },
        ]);
        setIsTyping(false);
      }, 800);
    }

    setLoading(false);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuestion(suggestion);
    inputRef.current?.focus();
  };

  const clearChat = () => {
    setMessages([]);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`app-container ${!showSidebar ? 'sidebar-hidden' : ''}`}>
      {/* Animated Background */}
      <div className="animated-bg">
        <div className="gradient-orb orb-1"></div>
        <div className="gradient-orb orb-2"></div>
        <div className="gradient-orb orb-3"></div>
        <div className="particle-container">
          {[...Array(20)].map((_, i) => (
            <div key={i} className="particle" style={{ animationDelay: `${i * 0.2}s` }}></div>
          ))}
        </div>
      </div>

      <div className="layout">
        {/* SIDEBAR */}
        <aside className={`sidebar ${showSidebar ? 'show' : 'hide'}`}>
          <div className="sidebar-header">
            <div className="logo-container">
              <div className="logo-icon">
                <span className="shield-icon">🛡️</span>
                <div className="logo-glow"></div>
              </div>
              <div className="logo-text">
                <h2>ICS Security</h2>
                <span className="logo-subtitle">AI Chatbot</span>
              </div>
            </div>
          </div>

          <div className="sidebar-content">
            <div className="info-cards">
              <div className="info-card card-gradient-1">
                <div className="card-icon">📅</div>
                <div className="card-content">
                  <h4>Thành lập</h4>
                  <p>03/2020</p>
                </div>
              </div>
              
              <div className="info-card card-gradient-2">
                <div className="card-icon">🏆</div>
                <div className="card-content">
                  <h4>Chứng nhận</h4>
                  <p>ISO 27001</p>
                </div>
              </div>
              
              <div className="info-card card-gradient-3">
                <div className="card-icon">🚀</div>
                <div className="card-content">
                  <h4>Sản phẩm</h4>
                  <p>VietGuard, AI SOC, SmartDashboard, CSA</p>
                </div>
              </div>
            </div>

            <div className="sidebar-actions">
              <button className="action-btn clear-btn" onClick={clearChat}>
                <span className="btn-icon">🗑️</span>
                <span>Xóa lịch sử</span>
              </button>
              
              <a
                href="https://icss.com.vn"
                target="_blank"
                className="action-btn website-btn"
              >
                <span className="btn-icon">🌐</span>
                <span>icss.com.vn</span>
              </a>
            </div>
          </div>

          <footer className="sidebar-footer">
            <div className="footer-content">
              <p>© 2026 ICS Security</p>
              <div className="footer-links">
                <span>Privacy</span>
                <span>•</span>
                <span>Terms</span>
              </div>
            </div>
          </footer>
        </aside>

        {/* Toggle Sidebar Button */}
        <button 
          className="sidebar-toggle" 
          onClick={() => setShowSidebar(!showSidebar)}
        >
          <span>{showSidebar ? '◀' : '▶'}</span>
        </button>

        {/* CHAT AREA */}
        <main className="chat-area">
          <div className="chat-header">
            <div className="header-content">
              <h1 className="chat-title">
                <span className="title-gradient">Trợ lý Ảo An Ninh Mạng ICS</span>
                <div className="status-indicator">
                  <span className="status-dot"></span>
                  <span className="status-text">Online</span>
                </div>
              </h1>
              <p className="subtitle">
                Hỗ trợ thông tin về VietGuard, AI SOC, SmartDashboard, CSA và chính sách bảo mật
              </p>
              
              {/* Chatbot mascot with greeting */}
              <div className="header-mascot">
                <div className="mascot-container">
                  <div className="greeting-arrow">
                    <span className="arrow-text">Loan đây!</span>
                    <span className="arrow-icon">👉</span>
                  </div>
                  <div className="chatbot-waving">
                    <span className="bot-emoji">🤖</span>
                    <span className="waving-hand">👋</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="chat-container">
            <div className="chat-box" ref={chatBoxRef}>
              {messages.length === 0 && (
                <div className="welcome-screen">
                  <div className="welcome-animation">
                    <div className="bot-avatar-large">
                      <span>🤖</span>
                      <div className="avatar-pulse"></div>
                    </div>
                    <h2>Xin chào! 👋</h2>
                    <p>Tôi là trợ lý AI 'Loan Yêu Thương' của ICS Security. Tôi có thể giúp bạn tìm hiểu về:</p>
                    <div className="features-grid">
                      <div className="feature-item">
                        <span className="feature-icon">🛡️</span>
                        <span>VietGuard</span>
                      </div>
                      <div className="feature-item">
                        <span className="feature-icon">🤖</span>
                        <span>AI SOC</span>
                      </div>
                      <div className="feature-item">
                        <span className="feature-icon">🔒</span>
                        <span>Bảo mật</span>
                      </div>
                      <div className="feature-item">
                        <span className="feature-icon">📊</span>
                        <span>Giải pháp</span>
                      </div>
                    </div>
                  </div>

                  <div className="suggested-questions">
                    <p className="suggestions-title">Câu hỏi gợi ý:</p>
                    <div className="suggestions-grid">
                      {suggestedQuestions.map((suggestion, index) => (
                        <button
                          key={index}
                          className="suggestion-chip"
                          onClick={() => handleSuggestionClick(suggestion)}
                        >
                          <span className="chip-icon">💡</span>
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={`message-wrapper ${m.role}`}>
                  <div className={`message ${m.role}`}>
                    <div className="message-avatar">
                      {m.role === "user" ? (
                        <span className="user-avatar">👤</span>
                      ) : (
                        <span className="bot-avatar">🤖</span>
                      )}
                    </div>
                    <div className="message-content">
                      <div className="message-header">
                        <span className="message-sender">
                          {m.role === "user" ? "Bạn" : "ICS Assistant"}
                        </span>
                        <span className="message-time">{formatTime(m.timestamp)}</span>
                      </div>
                      <div className="message-text">{m.text}</div>
                    </div>
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="message-wrapper bot">
                  <div className="message bot typing">
                    <div className="message-avatar">
                      <span className="bot-avatar">🤖</span>
                    </div>
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="input-container">
              <div className="input-box">
                <input
                  ref={inputRef}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Nhập câu hỏi của bạn..."
                  onKeyDown={(e) => e.key === "Enter" && !loading && sendMessage()}
                  disabled={loading}
                />
                <button 
                  onClick={() => sendMessage()} 
                  disabled={loading || !question.trim()}
                  className="send-button"
                >
                  {loading ? (
                    <span className="loading-spinner">⏳</span>
                  ) : (
                    <span className="send-icon">➤</span>
                  )}
                </button>
              </div>
              <p className="input-hint">
                Nhấn Enter để gửi • Hỗ trợ tiếng Việt
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}