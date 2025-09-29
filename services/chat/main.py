"""Chat Service for Second Brain Stack."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
from datetime import datetime

from core.database import DatabaseManager
from core.search import SearchService
from core.utils import get_logger

app = FastAPI(title="Second Brain Chat Service", version="1.0.0")
logger = get_logger(__name__)

# Global state
db_manager = None
search_service = None
active_sessions = {}


class ChatMessage(BaseModel):
    content: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    context_used: List[dict] = []
    timestamp: str


class ChatSession(BaseModel):
    session_id: str
    created_at: str
    message_count: int
    last_active: str


@app.on_event("startup")
async def startup_event():
    """Initialize the chat service."""
    global db_manager, search_service
    
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/brain.db")
    db_manager = DatabaseManager(database_url)
    search_service = SearchService(db_manager)
    
    logger.info("Chat service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "chat"}

@app.get("/")
async def root():
    """Root endpoint for basic service info."""
    return {"service": "chat", "version": "1.0.0", "status": "running"}

@app.post("/chat")
async def chat_endpoint(message: ChatMessage):
    """Simple chat endpoint for compatibility."""
    # Convert to message format and delegate
    return await send_message(message)


@app.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """Send a message to the chat system."""
    try:
        # Get or create session
        session_id = message.session_id or str(uuid.uuid4())
        
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "messages": [],
                "last_active": datetime.now().isoformat()
            }
        
        session = active_sessions[session_id]
        session["last_active"] = datetime.now().isoformat()
        session["messages"].append({
            "role": "user",
            "content": message.content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Search for relevant context
        search_results = await search_service.search_documents(
            query=message.content,
            search_type="hybrid",
            limit=3
        )
        
        # Generate response based on context
        if search_results:
            context_info = []
            response_parts = []
            
            response_parts.append(f"Based on your knowledge base, here's what I found about '{message.content}':")
            
            for i, result in enumerate(search_results[:3], 1):
                context_info.append({
                    "document_id": result["id"],
                    "title": result["title"],
                    "score": result["score"],
                    "source": result["source_path"]
                })
                
                response_parts.append(f"\n{i}. **{result['title']}** (Score: {result['score']:.2f})")
                response_parts.append(f"   From: {result['source_path']}")
                
                # Add relevant excerpt
                content = result["content"]
                if len(content) > 200:
                    content = content[:200] + "..."
                response_parts.append(f"   {content}")
            
            response = "\n".join(response_parts)
            
            if len(search_results) > 3:
                response += f"\n\n(Found {len(search_results)} total results, showing top 3)"
        else:
            response = f"I couldn't find specific information about '{message.content}' in your knowledge base. Try rephrasing your question or check if the relevant documents have been ingested."
            context_info = []
        
        # Store assistant response
        session["messages"].append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "context_used": context_info
        })
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            context_used=context_info,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error("Chat message failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/sessions", response_model=List[ChatSession])
async def get_sessions():
    """Get all active chat sessions."""
    try:
        sessions = []
        for session_id, session_data in active_sessions.items():
            sessions.append(ChatSession(
                session_id=session_id,
                created_at=session_data["created_at"],
                message_count=len(session_data["messages"]),
                last_active=session_data["last_active"]
            ))
        
        return sessions
        
    except Exception as e:
        logger.error("Failed to get sessions", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@app.get("/sessions/{session_id}")
async def get_session_history(session_id: str):
    """Get message history for a session."""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = active_sessions[session_id]
        return {
            "session_id": session_id,
            "created_at": session["created_at"],
            "last_active": session["last_active"],
            "messages": session["messages"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get session history", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get session history: {str(e)}")


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        del active_sessions[session_id]
        
        return {"message": f"Session {session_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete session", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)