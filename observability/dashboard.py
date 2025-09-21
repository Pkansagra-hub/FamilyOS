"""
Memory-Centric Observability Dashboard

Real-time dashboard for visualizing envelope processing through Memory Backbone architecture.
Provides comprehensive monitoring of Family AI cognitive processing and Memory Network operations.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse

from .envelope import MemoryEnvelope, CognitiveStage, PipelineStage
from .memory_trace import MemoryTracer
from .metrics import MetricsCollector


@dataclass
class DashboardMetrics:
    """Real-time dashboard metrics"""
    timestamp: float
    active_envelopes: int
    memory_operations_per_second: float
    cognitive_load: float
    family_sync_status: str
    pipeline_throughput: Dict[str, float]
    error_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnvelopeVisualization:
    """Envelope data optimized for dashboard visualization"""
    envelope_id: str
    cognitive_trace_id: str
    current_stage: str
    progress_percentage: float
    memory_operation: str
    api_plane: str
    processing_time: float
    family_context: bool
    error_state: Optional[str]
    transformation_count: int
    memory_spaces: List[str]
    
    @classmethod
    def from_envelope(cls, envelope: MemoryEnvelope) -> 'EnvelopeVisualization':
        """Create visualization data from memory envelope"""
        current_time = time.time()
        processing_time = current_time - envelope.created_at
        
        # Calculate progress based on transformations
        expected_stages = 8  # Rough estimate for complete processing
        progress = min(100.0, (len(envelope.transformations) / expected_stages) * 100)
        
        return cls(
            envelope_id=envelope.envelope_id,
            cognitive_trace_id=envelope.cognitive_trace_id,
            current_stage=envelope.current_stage or "initializing",
            progress_percentage=progress,
            memory_operation=envelope.memory_operation.value,
            api_plane=envelope.api_plane.value if envelope.api_plane else "unknown",
            processing_time=processing_time,
            family_context=bool(envelope.family_context),
            error_state=envelope.error_state,
            transformation_count=len(envelope.transformations),
            memory_spaces=envelope.memory_spaces.copy()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ObservabilityDashboard:
    """
    Real-time observability dashboard for Memory-Centric Family AI
    
    Provides comprehensive visualization of:
    - Envelope lifecycle tracking through Memory Backbone
    - Cognitive processing visualization 
    - Pipeline processing metrics
    - Family Memory Network status
    - Real-time Memory operations
    """
    
    def __init__(self, memory_tracer: MemoryTracer, metrics_collector: MetricsCollector):
        self.memory_tracer = memory_tracer
        self.metrics_collector = metrics_collector
        
        # Active tracking
        self.active_envelopes: Dict[str, MemoryEnvelope] = {}
        self.connected_clients: List[WebSocket] = []
        
        # Dashboard metrics cache
        self.metrics_history: List[DashboardMetrics] = []
        self.max_history_size = 1000
        
        # Family AI specific tracking
        self.family_device_status: Dict[str, Dict[str, Any]] = {}
        self.memory_backbone_health: Dict[str, Any] = {
            "memory_engine": {"status": "healthy", "load": 0.0},
            "cognitive_core": {"status": "healthy", "load": 0.0},
            "family_sync": {"status": "healthy", "last_sync": time.time()},
            "storage_layer": {"status": "healthy", "operations_per_sec": 0.0}
        }
        
        # Start background metrics collection
        self._start_metrics_collection()
    
    def track_envelope(self, envelope: MemoryEnvelope) -> None:
        """Track envelope for dashboard visualization"""
        self.active_envelopes[envelope.envelope_id] = envelope
        
        # Send real-time update to connected clients
        visualization = EnvelopeVisualization.from_envelope(envelope)
        asyncio.create_task(self._broadcast_envelope_update(visualization))
    
    def remove_envelope(self, envelope_id: str) -> None:
        """Remove completed envelope from tracking"""
        if envelope_id in self.active_envelopes:
            del self.active_envelopes[envelope_id]
            
            # Notify clients of completion
            asyncio.create_task(self._broadcast_envelope_completion(envelope_id))
    
    def update_family_device_status(self, device_id: str, status: Dict[str, Any]) -> None:
        """Update family device status for dashboard"""
        self.family_device_status[device_id] = {
            **status,
            "last_update": time.time(),
            "device_id": device_id
        }
        
        # Broadcast family network update
        asyncio.create_task(self._broadcast_family_update())
    
    def update_memory_backbone_health(self, component: str, health_data: Dict[str, Any]) -> None:
        """Update Memory Backbone component health"""
        if component in self.memory_backbone_health:
            self.memory_backbone_health[component].update(health_data)
            self.memory_backbone_health[component]["last_update"] = time.time()
            
            # Broadcast health update
            asyncio.create_task(self._broadcast_health_update())
    
    async def connect_websocket(self, websocket: WebSocket) -> None:
        """Connect new WebSocket client"""
        await websocket.accept()
        self.connected_clients.append(websocket)
        
        # Send initial dashboard state
        await self._send_initial_state(websocket)
    
    async def disconnect_websocket(self, websocket: WebSocket) -> None:
        """Disconnect WebSocket client"""
        if websocket in self.connected_clients:
            self.connected_clients.remove(websocket)
    
    async def _send_initial_state(self, websocket: WebSocket) -> None:
        """Send initial dashboard state to new client"""
        try:
            # Send active envelopes
            active_visualizations = [
                EnvelopeVisualization.from_envelope(envelope).to_dict()
                for envelope in self.active_envelopes.values()
            ]
            
            initial_state = {
                "type": "initial_state",
                "data": {
                    "active_envelopes": active_visualizations,
                    "metrics_history": [metrics.to_dict() for metrics in self.metrics_history[-50:]],
                    "family_devices": list(self.family_device_status.values()),
                    "memory_backbone_health": self.memory_backbone_health,
                    "dashboard_stats": {
                        "total_envelopes_tracked": len(self.active_envelopes),
                        "connected_clients": len(self.connected_clients),
                        "uptime": time.time() - getattr(self, 'start_time', time.time())
                    }
                }
            }
            
            await websocket.send_text(json.dumps(initial_state))
            
        except Exception as e:
            print(f"Error sending initial state: {e}")
    
    async def _broadcast_envelope_update(self, visualization: EnvelopeVisualization) -> None:
        """Broadcast envelope update to all connected clients"""
        message = {
            "type": "envelope_update",
            "data": visualization.to_dict()
        }
        await self._broadcast_message(message)
    
    async def _broadcast_envelope_completion(self, envelope_id: str) -> None:
        """Broadcast envelope completion"""
        message = {
            "type": "envelope_completed",
            "data": {"envelope_id": envelope_id, "timestamp": time.time()}
        }
        await self._broadcast_message(message)
    
    async def _broadcast_family_update(self) -> None:
        """Broadcast family device network update"""
        message = {
            "type": "family_update", 
            "data": {
                "devices": list(self.family_device_status.values()),
                "network_health": self._calculate_family_network_health()
            }
        }
        await self._broadcast_message(message)
    
    async def _broadcast_health_update(self) -> None:
        """Broadcast Memory Backbone health update"""
        message = {
            "type": "health_update",
            "data": self.memory_backbone_health
        }
        await self._broadcast_message(message)
    
    async def _broadcast_metrics_update(self, metrics: DashboardMetrics) -> None:
        """Broadcast metrics update"""
        message = {
            "type": "metrics_update",
            "data": metrics.to_dict()
        }
        await self._broadcast_message(message)
    
    async def _broadcast_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected WebSocket clients"""
        disconnected_clients = []
        
        for client in self.connected_clients:
            try:
                await client.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected_clients.append(client)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.disconnect_websocket(client)
    
    def _calculate_family_network_health(self) -> Dict[str, Any]:
        """Calculate overall family network health"""
        if not self.family_device_status:
            return {"status": "no_devices", "score": 0.0}
        
        current_time = time.time()
        healthy_devices = 0
        total_devices = len(self.family_device_status)
        
        for device_status in self.family_device_status.values():
            last_update = device_status.get("last_update", 0)
            if current_time - last_update < 300:  # 5 minutes threshold
                healthy_devices += 1
        
        health_score = (healthy_devices / total_devices) * 100 if total_devices > 0 else 0
        
        return {
            "status": "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "critical",
            "score": health_score,
            "healthy_devices": healthy_devices,
            "total_devices": total_devices
        }
    
    def _start_metrics_collection(self) -> None:
        """Start background metrics collection"""
        self.start_time = time.time()
        
        async def collect_metrics():
            while True:
                try:
                    # Collect current metrics
                    current_time = time.time()
                    
                    # Calculate envelope throughput
                    recent_envelopes = [
                        env for env in self.active_envelopes.values()
                        if current_time - env.created_at < 60  # Last minute
                    ]
                    
                    # Calculate pipeline throughput
                    pipeline_throughput = {}
                    for stage in PipelineStage:
                        stage_count = sum(
                            1 for env in recent_envelopes
                            for trans in env.transformations
                            if trans.stage == stage.value
                        )
                        pipeline_throughput[stage.value] = stage_count / 60.0  # per second
                    
                    # Calculate error rate
                    error_envelopes = sum(1 for env in recent_envelopes if env.error_state)
                    error_rate = (error_envelopes / len(recent_envelopes)) * 100 if recent_envelopes else 0
                    
                    # Create dashboard metrics
                    metrics = DashboardMetrics(
                        timestamp=current_time,
                        active_envelopes=len(self.active_envelopes),
                        memory_operations_per_second=len(recent_envelopes) / 60.0,
                        cognitive_load=self._calculate_cognitive_load(),
                        family_sync_status=self._get_family_sync_status(),
                        pipeline_throughput=pipeline_throughput,
                        error_rate=error_rate
                    )
                    
                    # Store metrics
                    self.metrics_history.append(metrics)
                    if len(self.metrics_history) > self.max_history_size:
                        self.metrics_history.pop(0)
                    
                    # Broadcast metrics update
                    await self._broadcast_metrics_update(metrics)
                    
                except Exception as e:
                    print(f"Error collecting metrics: {e}")
                
                await asyncio.sleep(5)  # Collect every 5 seconds
        
        # Start metrics collection task
        asyncio.create_task(collect_metrics())
    
    def _calculate_cognitive_load(self) -> float:
        """Calculate current cognitive processing load"""
        if not self.active_envelopes:
            return 0.0
        
        # Calculate load based on active cognitive processing
        cognitive_envelopes = [
            env for env in self.active_envelopes.values()
            if env.current_stage and any(
                stage.value in env.current_stage for stage in CognitiveStage
            )
        ]
        
        # Normalize load (0-100%)
        max_cognitive_capacity = 100  # Arbitrary max for visualization
        current_load = len(cognitive_envelopes)
        
        return min(100.0, (current_load / max_cognitive_capacity) * 100)
    
    def _get_family_sync_status(self) -> str:
        """Get current family synchronization status"""
        family_health = self._calculate_family_network_health()
        
        if family_health["status"] == "healthy":
            return "synced"
        elif family_health["status"] == "degraded":
            return "partial_sync"
        else:
            return "sync_issues"


def create_dashboard_app(dashboard: ObservabilityDashboard) -> FastAPI:
    """Create FastAPI application for observability dashboard"""
    
    app = FastAPI(title="Memory-Centric Family AI Observability Dashboard")
    
    # Dashboard HTML template
    dashboard_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Memory-Centric Family AI Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a1a; color: #fff; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .metric-card { background: #2a2a2a; border-radius: 8px; padding: 20px; border-left: 4px solid #00ff88; }
            .metric-value { font-size: 2em; font-weight: bold; color: #00ff88; }
            .metric-label { color: #aaa; margin-top: 5px; }
            .envelopes-section { background: #2a2a2a; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
            .envelope-item { background: #3a3a3a; border-radius: 4px; padding: 15px; margin: 10px 0; border-left: 4px solid #0088ff; }
            .envelope-header { display: flex; justify-content: between; align-items: center; margin-bottom: 10px; }
            .envelope-id { font-weight: bold; color: #0088ff; }
            .envelope-stage { color: #ff8800; }
            .progress-bar { width: 100%; height: 8px; background: #555; border-radius: 4px; overflow: hidden; }
            .progress-fill { height: 100%; background: linear-gradient(90deg, #00ff88, #0088ff); transition: width 0.3s; }
            .family-devices { background: #2a2a2a; border-radius: 8px; padding: 20px; }
            .device-item { background: #3a3a3a; border-radius: 4px; padding: 10px; margin: 5px 0; display: flex; justify-content: space-between; }
            .status-healthy { color: #00ff88; }
            .status-degraded { color: #ff8800; }
            .status-critical { color: #ff4444; }
            .connection-status { position: fixed; top: 10px; right: 10px; padding: 10px; border-radius: 4px; }
            .connected { background: #00ff88; color: #000; }
            .disconnected { background: #ff4444; color: #fff; }
        </style>
    </head>
    <body>
        <div class="connection-status" id="connectionStatus">Connecting...</div>
        
        <div class="container">
            <div class="header">
                <h1>🧠 Memory-Centric Family AI Dashboard</h1>
                <p>Real-time observability for Memory Backbone & Cognitive Processing</p>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" id="activeEnvelopes">0</div>
                    <div class="metric-label">Active Envelopes</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="memoryOpsPerSec">0.0</div>
                    <div class="metric-label">Memory Ops/Sec</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="cognitiveLoad">0%</div>
                    <div class="metric-label">Cognitive Load</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="familySyncStatus">Unknown</div>
                    <div class="metric-label">Family Sync Status</div>
                </div>
            </div>
            
            <div class="envelopes-section">
                <h3>📨 Active Memory Envelopes</h3>
                <div id="activeEnvelopesList">
                    <p>No active envelopes</p>
                </div>
            </div>
            
            <div class="family-devices">
                <h3>👨‍👩‍👧‍👦 Family Device Network</h3>
                <div id="familyDevicesList">
                    <p>No family devices connected</p>
                </div>
            </div>
        </div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8000/ws/dashboard');
            const connectionStatus = document.getElementById('connectionStatus');
            
            ws.onopen = function(event) {
                connectionStatus.textContent = 'Connected';
                connectionStatus.className = 'connection-status connected';
            };
            
            ws.onclose = function(event) {
                connectionStatus.textContent = 'Disconnected';
                connectionStatus.className = 'connection-status disconnected';
            };
            
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                
                if (message.type === 'initial_state') {
                    updateDashboard(message.data);
                } else if (message.type === 'metrics_update') {
                    updateMetrics(message.data);
                } else if (message.type === 'envelope_update') {
                    updateEnvelope(message.data);
                } else if (message.type === 'family_update') {
                    updateFamilyDevices(message.data.devices);
                }
            };
            
            function updateDashboard(data) {
                updateMetrics(data.metrics_history[data.metrics_history.length - 1] || {});
                updateEnvelopes(data.active_envelopes || []);
                updateFamilyDevices(data.family_devices || []);
            }
            
            function updateMetrics(metrics) {
                document.getElementById('activeEnvelopes').textContent = metrics.active_envelopes || 0;
                document.getElementById('memoryOpsPerSec').textContent = (metrics.memory_operations_per_second || 0).toFixed(1);
                document.getElementById('cognitiveLoad').textContent = (metrics.cognitive_load || 0).toFixed(0) + '%';
                document.getElementById('familySyncStatus').textContent = metrics.family_sync_status || 'Unknown';
            }
            
            function updateEnvelopes(envelopes) {
                const container = document.getElementById('activeEnvelopesList');
                
                if (envelopes.length === 0) {
                    container.innerHTML = '<p>No active envelopes</p>';
                    return;
                }
                
                container.innerHTML = envelopes.map(env => `
                    <div class="envelope-item" id="envelope-${env.envelope_id}">
                        <div class="envelope-header">
                            <span class="envelope-id">${env.envelope_id.substring(0, 8)}...</span>
                            <span class="envelope-stage">${env.current_stage}</span>
                        </div>
                        <div>Operation: ${env.memory_operation} | Plane: ${env.api_plane}</div>
                        <div>Processing: ${env.processing_time.toFixed(2)}s | Transformations: ${env.transformation_count}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${env.progress_percentage}%"></div>
                        </div>
                    </div>
                `).join('');
            }
            
            function updateEnvelope(envelope) {
                const container = document.getElementById('activeEnvelopesList');
                const existingElement = document.getElementById(`envelope-${envelope.envelope_id}`);
                
                const envelopeHtml = `
                    <div class="envelope-item" id="envelope-${envelope.envelope_id}">
                        <div class="envelope-header">
                            <span class="envelope-id">${envelope.envelope_id.substring(0, 8)}...</span>
                            <span class="envelope-stage">${envelope.current_stage}</span>
                        </div>
                        <div>Operation: ${envelope.memory_operation} | Plane: ${envelope.api_plane}</div>
                        <div>Processing: ${envelope.processing_time.toFixed(2)}s | Transformations: ${envelope.transformation_count}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${envelope.progress_percentage}%"></div>
                        </div>
                    </div>
                `;
                
                if (existingElement) {
                    existingElement.outerHTML = envelopeHtml;
                } else {
                    container.innerHTML += envelopeHtml;
                }
            }
            
            function updateFamilyDevices(devices) {
                const container = document.getElementById('familyDevicesList');
                
                if (devices.length === 0) {
                    container.innerHTML = '<p>No family devices connected</p>';
                    return;
                }
                
                container.innerHTML = devices.map(device => `
                    <div class="device-item">
                        <span>${device.device_id}</span>
                        <span class="status-healthy">Online</span>
                    </div>
                `).join('');
            }
        </script>
    </body>
    </html>
    '''
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard_page(request: Request):
        """Serve dashboard HTML page"""
        return HTMLResponse(content=dashboard_html)
    
    @app.websocket("/ws/dashboard")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time dashboard updates"""
        await dashboard.connect_websocket(websocket)
        
        try:
            while True:
                # Keep connection alive and handle any client messages
                await websocket.receive_text()
        except WebSocketDisconnect:
            await dashboard.disconnect_websocket(websocket)
    
    @app.get("/api/envelopes")
    async def get_active_envelopes():
        """API endpoint to get active envelopes"""
        return {
            "active_envelopes": [
                EnvelopeVisualization.from_envelope(env).to_dict()
                for env in dashboard.active_envelopes.values()
            ]
        }
    
    @app.get("/api/metrics")
    async def get_current_metrics():
        """API endpoint to get current metrics"""
        if dashboard.metrics_history:
            return dashboard.metrics_history[-1].to_dict()
        return {}
    
    @app.get("/api/health")
    async def get_system_health():
        """API endpoint for system health check"""
        return {
            "status": "healthy",
            "memory_backbone": dashboard.memory_backbone_health,
            "family_network": dashboard._calculate_family_network_health(),
            "active_envelopes": len(dashboard.active_envelopes),
            "connected_clients": len(dashboard.connected_clients)
        }
    
    return app


# Global dashboard instance (to be initialized)
_dashboard_instance: Optional[ObservabilityDashboard] = None

def get_dashboard() -> ObservabilityDashboard:
    """Get global dashboard instance"""
    global _dashboard_instance
    if _dashboard_instance is None:
        from .memory_trace import get_tracer
        from .metrics import metrics_collector
        _dashboard_instance = ObservabilityDashboard(get_tracer(), metrics_collector)
    return _dashboard_instance