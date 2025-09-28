"""API Gateway for Second Brain Stack."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import httpx
import os

app = FastAPI(title="Second Brain Gateway", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs from environment
SERVICES = {
    "ingestion": os.getenv("INGESTION_SERVICE_URL", "http://localhost:8001"),
    "search": os.getenv("SEARCH_SERVICE_URL", "http://localhost:8002"),
    "knowledge": os.getenv("KNOWLEDGE_SERVICE_URL", "http://localhost:8003"),
    "chat": os.getenv("CHAT_SERVICE_URL", "http://localhost:8004"),
}


@app.get("/")
async def root():
    """Gateway root endpoint."""
    return {
        "service": "Second Brain Gateway",
        "version": "1.0.0",
        "status": "running",
        "services": SERVICES
    }


@app.get("/health")
async def health():
    """Health check for all services."""
    health_status = {"gateway": "healthy", "services": {}}
    
    async with httpx.AsyncClient() as client:
        for service_name, service_url in SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=5.0)
                if response.status_code == 200:
                    health_status["services"][service_name] = "healthy"
                else:
                    health_status["services"][service_name] = f"unhealthy ({response.status_code})"
            except Exception as e:
                health_status["services"][service_name] = f"error ({str(e)})"
    
    return health_status


# Proxy endpoints to services
@app.api_route("/api/ingest/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_ingestion(path: str, request: Request):
    """Proxy requests to ingestion service."""
    return await proxy_request("ingestion", path, request)


@app.api_route("/api/search/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_search(path: str, request: Request):
    """Proxy requests to search service."""
    return await proxy_request("search", path, request)


@app.api_route("/api/knowledge/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_knowledge(path: str, request: Request):
    """Proxy requests to knowledge service."""
    return await proxy_request("knowledge", path, request)


@app.api_route("/api/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_chat(path: str, request: Request):
    """Proxy requests to chat service."""
    return await proxy_request("chat", path, request)


async def proxy_request(service_name: str, path: str, request: Request):
    """Proxy HTTP request to a service."""
    service_url = SERVICES.get(service_name)
    if not service_url:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    url = f"{service_url}/{path}"
    
    # Get request data
    body = await request.body()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                headers=dict(request.headers),
                content=body,
                timeout=30.0
            )
            return response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Service {service_name} unavailable: {str(e)}")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple dashboard for the Second Brain Stack."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Second Brain Stack Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
            .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                       gap: 20px; margin-bottom: 30px; }
            .service { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .service h3 { color: #333; margin-top: 0; }
            .status { padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }
            .healthy { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .endpoints { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .endpoint { margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧠 Second Brain Stack Dashboard</h1>
                <p>Microservices Architecture for Knowledge Management</p>
            </div>
            
            <div class="services">
                <div class="service">
                    <h3>📥 Ingestion Service</h3>
                    <p>Document processing and ingestion</p>
                    <span class="status healthy">Port 8001</span>
                </div>
                
                <div class="service">
                    <h3>🔍 Search Service</h3>
                    <p>Full-text and semantic search</p>
                    <span class="status healthy">Port 8002</span>
                </div>
                
                <div class="service">
                    <h3>🕸️ Knowledge Service</h3>
                    <p>Knowledge graph and entities</p>
                    <span class="status healthy">Port 8003</span>
                </div>
                
                <div class="service">
                    <h3>💬 Chat Service</h3>
                    <p>Conversational interface</p>
                    <span class="status healthy">Port 8004</span>
                </div>
            </div>
            
            <div class="endpoints">
                <h3>🔗 API Endpoints</h3>
                <div class="endpoint">GET /health - Health check for all services</div>
                <div class="endpoint">POST /api/ingest/documents - Ingest documents</div>
                <div class="endpoint">GET /api/search/query?q=... - Search documents</div>
                <div class="endpoint">GET /api/knowledge/entities - Get entities</div>
                <div class="endpoint">POST /api/chat/message - Chat with knowledge base</div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)