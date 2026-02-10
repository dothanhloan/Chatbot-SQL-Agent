import { useState, useEffect, useRef } from "react";
import "./App.css";

const API_URL = `${import.meta.env.VITE_API_BASE}/chat`;




interface Message {
  role: "user" | "bot";
  text: string;
  timestamp: Date;
  downloadUrl?: string;
  fullText?: string;
  stopped?: boolean;
}

const suggestedQuestions = [
  "ICS là gì?",
  "Danh sách phòng ban?",
  "Danh sách dự án trễ hạn?",
  "Công việc nào chưa xong?",
];

export default function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const chatBoxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const typingIntervalRef = useRef<number | null>(null);

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

    // Nếu đang có typing interval cũ thì clear
    if (typingIntervalRef.current !== null) {
      clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }

    // Tạo AbortController mới cho request này
    abortControllerRef.current = new AbortController();

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: messageText }),
        signal: abortControllerRef.current.signal, // Truyền signal để có thể cancel
      });

      const data = await res.json();

      const fullText: string = data.answer || "";
      const downloadUrl: string | undefined = data.download_url || undefined;

      // Thêm message bot rỗng để fill dần dần
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: "",
          timestamp: new Date(),
          downloadUrl,
          fullText,
          stopped: false,
        },
      ]);

      let index = 0;
      const step = 3; // số ký tự mỗi lần cập nhật
      typingIntervalRef.current = window.setInterval(() => {
        index += step;
        setMessages((prev) => {
          if (prev.length === 0) return prev;
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          const last = newMessages[lastIndex];
          const nextText = fullText.slice(0, index);
          newMessages[lastIndex] = { ...last, text: nextText };
          return newMessages;
        });

        if (index >= fullText.length) {
          if (typingIntervalRef.current !== null) {
            clearInterval(typingIntervalRef.current);
            typingIntervalRef.current = null;
          }
          setIsTyping(false);
          setLoading(false);
        }
      }, 20);
    } catch (err: any) {
      // Nếu bị abort (cancel), không hiển thị thông báo lỗi
      if (err.name === "AbortError") {
        setIsTyping(false);
        setLoading(false);
      } else {
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            { role: "bot", text: "❌ Lỗi kết nối backend. Vui lòng thử lại sau.", timestamp: new Date() },
          ]);
          setIsTyping(false);
          setLoading(false);
        }, 800);
      }
    }
  };

  // Hàm dừng chat
  const stopChat = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (typingIntervalRef.current !== null) {
      clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }

    // Đánh dấu message bot gần nhất là đã dừng
    setMessages((prev) => {
      const arr = [...prev];
      for (let i = arr.length - 1; i >= 0; i--) {
        const msg = arr[i];
        if (msg.role === "bot" && msg.fullText && !msg.stopped) {
          arr[i] = { ...msg, stopped: true };
          break;
        }
      }
      return arr;
    });

    setLoading(false);
    setIsTyping(false);
  };

  // Tiếp tục trả lời phần còn lại của một message đã bị dừng
  const resumeMessage = (messageIndex: number) => {
    setLoading(true);
    setIsTyping(true);

    if (typingIntervalRef.current !== null) {
      clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }

    typingIntervalRef.current = window.setInterval(() => {
      setMessages((prev) => {
        const arr = [...prev];
        const msg = arr[messageIndex];
        if (!msg || !msg.fullText) {
          return prev;
        }

        const currentLength = msg.text.length;
        const step = 3;
        const nextLength = Math.min(currentLength + step, msg.fullText.length);
        const nextText = msg.fullText.slice(0, nextLength);

        arr[messageIndex] = {
          ...msg,
          text: nextText,
          stopped: false, // sau khi bấm Thử lại thì không hiện dòng thông báo nữa
        };

        if (nextLength >= msg.fullText.length) {
          if (typingIntervalRef.current !== null) {
            clearInterval(typingIntervalRef.current);
            typingIntervalRef.current = null;
          }
          setIsTyping(false);
          setLoading(false);
        }

        return arr;
      });
    }, 20);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuestion(suggestion);
    inputRef.current?.focus();
  };

  const clearChat = () => {
    setMessages([]);
  };

  const startVoiceRecognition = () => {
    // Kiểm tra hỗ trợ Web Speech API
    const SpeechRecognition = window.SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      alert("Trình duyệt của bạn không hỗ trợ nhập giọng nói. Vui lòng sử dụng Chrome, Edge hoặc Safari.");
      return;
    }

    if (isListening) {
      // Dừng lắng nghe
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'vi-VN';
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        
        if (event.results[i].isFinal) {
          setQuestion(prev => (prev + ' ' + transcript).trim());
        } else {
          interimTranscript += transcript;
        }
      }
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error', event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
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
                  <p>2021</p>
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
                  <p>VietGuard, AI SOC, SmartDashboard, Oracle Cloud</p>
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
                Trợ lý AI quản lý nhân sự - Hỗ trợ truy vấn và quản lý thông tin toàn diện
              </p>
              
              {/* Chatbot mascot with greeting */}
              <div className="header-mascot">
                <div className="mascot-container">
                  <div className="greeting-arrow">
                    <span className="arrow-text">Trợ lý AI đây!</span>
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
                    <p>Tôi là trợ lý AI của ICS Security. Tôi có thể giúp bạn tìm hiểu về:</p>
                    <div className="features-grid">
                      <div className="feature-item">
                        <span className="feature-icon">👨‍💼</span>
                        <span>Nhân sự</span>
                      </div>
                      <div className="feature-item">
                        <span className="feature-icon">📋</span>
                        <span>Dự án</span>
                      </div>
                      <div className="feature-item">
                        <span className="feature-icon">🏢</span>
                        <span>Phòng ban</span>
                      </div>
                      <div className="feature-item">
                        <span className="feature-icon">💡</span>
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
                        <span className="user-avatar">👑</span>
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
                      <div className="message-text">
                        {m.text}
                        {m.stopped && m.fullText && (
                          <div className="stop-note-row">
                            <span className="stop-note-text">Bạn đã dừng câu trả lời này</span>
                            <button
                              className="retry-button"
                              onClick={() => resumeMessage(i)}
                            >
                              ⟳ Thử lại
                            </button>
                          </div>
                        )}
                      </div>
                      {m.downloadUrl && (
                        <button 
                          className="download-button"
                          onClick={() => {
                            const baseUrl = import.meta.env.VITE_API_BASE || "http://localhost:8000";
                            window.location.href = `${baseUrl}${m.downloadUrl}`;
                          }}
                        >
                          📥 Tải file Word
                        </button>
                      )}
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
                <textarea
                  ref={inputRef}
                  value={question}
                  onChange={(e) => {
                    setQuestion(e.target.value);
                    // Auto-expand textarea
                    e.target.style.height = 'auto';
                    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
                  }}
                  placeholder="Nhập câu hỏi của bạn..."
                  onKeyDown={(e) => {
                    // Enter gửi, Shift+Enter xuống dòng
                    if (e.key === "Enter" && !e.shiftKey && !loading) {
                      sendMessage();
                      e.preventDefault();
                    }
                  }}
                  disabled={loading}
                  className="message-input"
                />
                <button
                  onClick={startVoiceRecognition}
                  className={`voice-button ${isListening ? 'listening' : ''}`}
                  title={isListening ? "Dừng lắng nghe" : "Nhập bằng giọng nói"}
                  disabled={loading}
                >
                  <span className="voice-icon">{isListening ? '🎙️' : '🎤'}</span>
                </button>
                {loading ? (
                  <button 
                    onClick={stopChat}
                    className="stop-button"
                    title="Dừng chat"
                  >
                    <span className="stop-icon">⏹️</span>
                  </button>
                ) : (
                  <button 
                    onClick={() => sendMessage()} 
                    disabled={!question.trim()}
                    className="send-button"
                  >
                    <span className="send-icon">➤</span>
                  </button>
                )}
              </div>
              <p className="input-hint">
                Enter để gửi • Shift+Enter xuống dòng • 🎤 để nhập giọng nói {loading && "• Nhấn nút ⏹️ để dừng"}
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}