"""
Memory-Centric Metrics Collection
================================

Prometheus-based metrics specifically designed for Family AI Memory Backbone.
Tracks cognitive performance, memory operations, and family intelligence coordination.

Key Features:
- Pipeline Metrics: Instrumentation for all 20 specialized pipelines
- Memory Metrics: Submit, recall, consolidate, sync operation metrics
- Cognitive Load: Working memory, attention, and emotional processing metrics
- Family Intelligence: Cross-device coordination and context metrics
- SLO Tracking: Service level objectives for Memory Backbone operations
"""

from enum import Enum

# Prometheus imports
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    start_http_server, CollectorRegistry, REGISTRY
)

from .envelope import MemoryEnvelope

class MetricType(Enum):
    """Types of metrics for Memory Backbone operations"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"
    INFO = "info"

class MemoryMetrics:
    """
    Memory operation metrics for Family AI Memory Backbone
    Tracks memory submit, recall, consolidate, and sync operations
    """
    
    def __init__(self, registry: CollectorRegistry = REGISTRY):
        self.registry = registry
        
        # Memory Operation Counters
        self.memory_operations_total = Counter(
            name='memory_operations_total',
            documentation='Total number of memory operations',
            labelnames=['operation', 'api_plane', 'success', 'memory_space'],
            registry=registry
        )
        
        # Memory Operation Duration
        self.memory_operation_duration = Histogram(
            name='memory_operation_duration_seconds',
            documentation='Duration of memory operations in seconds',
            labelnames=['operation', 'api_plane', 'memory_space'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=registry
        )
        
        # Memory Storage Metrics
        self.memory_storage_size = Gauge(
            name='memory_storage_size_bytes',
            documentation='Current memory storage size in bytes',
            labelnames=['storage_type', 'memory_space'],
            registry=registry
        )
        
        # Memory Recall Quality
        self.memory_recall_relevance = Histogram(
            name='memory_recall_relevance_score',
            documentation='Relevance score of recalled memories',
            labelnames=['memory_space', 'recall_type'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=registry
        )
        
        # Family Sync Metrics
        self.family_sync_operations = Counter(
            name='family_sync_operations_total',
            documentation='Total family synchronization operations',
            labelnames=['source_device', 'target_device', 'sync_type', 'success'],
            registry=registry
        )
        
        self.family_sync_duration = Histogram(
            name='family_sync_duration_seconds',
            documentation='Duration of family synchronization in seconds',
            labelnames=['sync_type', 'device_count'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=registry
        )
        
        # Memory Consolidation Metrics
        self.memory_consolidation_events = Counter(
            name='memory_consolidation_events_total',
            documentation='Total memory consolidation events',
            labelnames=['consolidation_type', 'trigger'],
            registry=registry
        )
        
    def record_memory_operation(self, 
                              operation: str,
                              api_plane: str,
                              memory_space: str,
                              duration: float,
                              success: bool) -> None:
        """Record a memory operation"""
        self.memory_operations_total.labels(
            operation=operation,
            api_plane=api_plane,
            success=str(success),
            memory_space=memory_space
        ).inc()
        
        if success:
            self.memory_operation_duration.labels(
                operation=operation,
                api_plane=api_plane,
                memory_space=memory_space
            ).observe(duration)
    
    def record_memory_recall(self, 
                           memory_space: str,
                           recall_type: str,
                           relevance_score: float) -> None:
        """Record memory recall quality"""
        self.memory_recall_relevance.labels(
            memory_space=memory_space,
            recall_type=recall_type
        ).observe(relevance_score)
    
    def update_memory_storage(self, storage_type: str, memory_space: str, size_bytes: int) -> None:
        """Update memory storage size"""
        self.memory_storage_size.labels(
            storage_type=storage_type,
            memory_space=memory_space
        ).set(size_bytes)
    
    def record_family_sync(self, 
                          source_device: str,
                          target_device: str,
                          sync_type: str,
                          duration: float,
                          device_count: int,
                          success: bool) -> None:
        """Record family synchronization event"""
        self.family_sync_operations.labels(
            source_device=source_device,
            target_device=target_device,
            sync_type=sync_type,
            success=str(success)
        ).inc()
        
        if success:
            self.family_sync_duration.labels(
                sync_type=sync_type,
                device_count=str(device_count)
            ).observe(duration)

class PipelineMetrics:
    """
    Pipeline performance metrics for all 20 specialized pipelines
    Tracks processing performance, cognitive load, and throughput
    """
    
    def __init__(self, registry: CollectorRegistry = REGISTRY):
        self.registry = registry
        
        # Pipeline Processing Counters
        self.pipeline_processes_total = Counter(
            name='pipeline_processes_total',
            documentation='Total number of pipeline processes',
            labelnames=['pipeline', 'stage', 'success'],
            registry=registry
        )
        
        # Pipeline Processing Duration
        self.pipeline_duration = Histogram(
            name='pipeline_duration_seconds',
            documentation='Duration of pipeline processing in seconds',
            labelnames=['pipeline', 'stage'],
            buckets=[0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=registry
        )
        
        # Pipeline Queue Depth
        self.pipeline_queue_depth = Gauge(
            name='pipeline_queue_depth',
            documentation='Current queue depth for pipeline',
            labelnames=['pipeline'],
            registry=registry
        )
        
        # Pipeline Throughput
        self.pipeline_throughput = Gauge(
            name='pipeline_throughput_per_second',
            documentation='Current throughput for pipeline in operations per second',
            labelnames=['pipeline'],
            registry=registry
        )
        
        # Pipeline Error Rate
        self.pipeline_error_rate = Gauge(
            name='pipeline_error_rate_percent',
            documentation='Current error rate for pipeline as percentage',
            labelnames=['pipeline'],
            registry=registry
        )
        
    def record_pipeline_process(self, 
                              pipeline: str,
                              stage: str,
                              duration: float,
                              success: bool) -> None:
        """Record pipeline processing event"""
        self.pipeline_processes_total.labels(
            pipeline=pipeline,
            stage=stage,
            success=str(success)
        ).inc()
        
        if success:
            self.pipeline_duration.labels(
                pipeline=pipeline,
                stage=stage
            ).observe(duration)
    
    def update_pipeline_queue(self, pipeline: str, depth: int) -> None:
        """Update pipeline queue depth"""
        self.pipeline_queue_depth.labels(pipeline=pipeline).set(depth)
        
    def update_pipeline_throughput(self, pipeline: str, ops_per_second: float) -> None:
        """Update pipeline throughput"""
        self.pipeline_throughput.labels(pipeline=pipeline).set(ops_per_second)
        
    def update_pipeline_error_rate(self, pipeline: str, error_rate_percent: float) -> None:
        """Update pipeline error rate"""
        self.pipeline_error_rate.labels(pipeline=pipeline).set(error_rate_percent)

class CognitiveMetrics:
    """
    Cognitive processing metrics for brain-inspired architecture
    Tracks attention, working memory, and emotional intelligence
    """
    
    def __init__(self, registry: CollectorRegistry = REGISTRY):
        self.registry = registry
        
        # Attention Gate Metrics
        self.attention_decisions = Counter(
            name='attention_decisions_total',
            documentation='Total attention gate decisions',
            labelnames=['decision', 'salience_level'],
            registry=registry
        )
        
        self.attention_processing_time = Histogram(
            name='attention_processing_time_seconds',
            documentation='Time to process attention decisions',
            labelnames=['decision_type'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5],
            registry=registry
        )
        
        # Working Memory Metrics
        self.working_memory_usage = Gauge(
            name='working_memory_usage_percent',
            documentation='Current working memory usage percentage',
            registry=registry
        )
        
        self.working_memory_operations = Counter(
            name='working_memory_operations_total',
            documentation='Total working memory operations',
            labelnames=['operation', 'success'],
            registry=registry
        )
        
        # Emotional Intelligence Metrics
        self.emotional_states = Gauge(
            name='emotional_state_intensity',
            documentation='Current emotional state intensity',
            labelnames=['emotion', 'user_id'],
            registry=registry
        )
        
        self.emotional_transitions = Counter(
            name='emotional_transitions_total',
            documentation='Total emotional state transitions',
            labelnames=['from_state', 'to_state', 'user_id'],
            registry=registry
        )
        
    def record_attention_decision(self, 
                                decision: str,
                                salience_level: str,
                                processing_time: float) -> None:
        """Record attention gate decision"""
        self.attention_decisions.labels(
            decision=decision,
            salience_level=salience_level
        ).inc()
        
        self.attention_processing_time.labels(
            decision_type=decision
        ).observe(processing_time)
    
    def update_working_memory(self, usage_percent: float) -> None:
        """Update working memory usage"""
        self.working_memory_usage.set(usage_percent)
    
    def record_working_memory_operation(self, operation: str, success: bool) -> None:
        """Record working memory operation"""
        self.working_memory_operations.labels(
            operation=operation,
            success=str(success)
        ).inc()
    
    def update_emotional_state(self, emotion: str, user_id: str, intensity: float) -> None:
        """Update emotional state intensity"""
        self.emotional_states.labels(
            emotion=emotion,
            user_id=user_id
        ).set(intensity)
    
    def record_emotional_transition(self, 
                                  from_state: str,
                                  to_state: str,
                                  user_id: str) -> None:
        """Record emotional state transition"""
        self.emotional_transitions.labels(
            from_state=from_state,
            to_state=to_state,
            user_id=user_id
        ).inc()

class FamilyIntelligenceMetrics:
    """
    Family coordination and intelligence metrics
    Tracks cross-device communication and family context
    """
    
    def __init__(self, registry: CollectorRegistry = REGISTRY):
        self.registry = registry
        
        # Family Device Metrics
        self.family_devices_active = Gauge(
            name='family_devices_active',
            documentation='Number of active family devices',
            labelnames=['family_id'],
            registry=registry
        )
        
        self.family_context_updates = Counter(
            name='family_context_updates_total',
            documentation='Total family context updates',
            labelnames=['family_id', 'context_type'],
            registry=registry
        )
        
        # Cross-Device Communication
        self.cross_device_messages = Counter(
            name='cross_device_messages_total',
            documentation='Total cross-device messages',
            labelnames=['source_device', 'target_device', 'message_type'],
            registry=registry
        )
        
        self.cross_device_latency = Histogram(
            name='cross_device_latency_seconds',
            documentation='Cross-device communication latency',
            labelnames=['communication_type'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
            registry=registry
        )
        
    def update_active_devices(self, family_id: str, device_count: int) -> None:
        """Update active family devices count"""
        self.family_devices_active.labels(family_id=family_id).set(device_count)
    
    def record_context_update(self, family_id: str, context_type: str) -> None:
        """Record family context update"""
        self.family_context_updates.labels(
            family_id=family_id,
            context_type=context_type
        ).inc()
    
    def record_cross_device_message(self, 
                                  source_device: str,
                                  target_device: str,
                                  message_type: str,
                                  latency: float) -> None:
        """Record cross-device communication"""
        self.cross_device_messages.labels(
            source_device=source_device,
            target_device=target_device,
            message_type=message_type
        ).inc()
        
        self.cross_device_latency.labels(
            communication_type=message_type
        ).observe(latency)

class MetricsCollector:
    """
    Centralized metrics collector for Family AI Memory Backbone
    Coordinates all metric collection and provides unified interface
    """
    
    def __init__(self, metrics_port: int = 8000):
        self.metrics_port = metrics_port
        self.registry = CollectorRegistry()
        
        # Initialize metric collectors
        self.memory_metrics = MemoryMetrics(self.registry)
        self.pipeline_metrics = PipelineMetrics(self.registry)
        self.cognitive_metrics = CognitiveMetrics(self.registry)
        self.family_metrics = FamilyIntelligenceMetrics(self.registry)
        
        # System info
        self.system_info = Info(
            name='family_ai_system_info',
            documentation='Family AI System Information',
            registry=self.registry
        )
        
        self.system_info.info({
            'version': '1.0.0',
            'architecture': 'memory_backbone',
            'pipelines': '20',
            'api_planes': '3',
            'family_ai': 'true'
        })
        
    def start_metrics_server(self) -> None:
        """Start Prometheus metrics server"""
        start_http_server(self.metrics_port, registry=self.registry)
        print(f"Metrics server started on port {self.metrics_port}")
    
    def record_envelope_metrics(self, envelope: MemoryEnvelope) -> None:
        """Record comprehensive metrics for envelope processing"""
        if not envelope.transformations:
            return
            
        # Record memory operation
        if envelope.api_plane and envelope.memory_operation:
            self.memory_metrics.record_memory_operation(
                operation=envelope.memory_operation.value,
                api_plane=envelope.api_plane.value,
                memory_space=envelope.memory_spaces[0] if envelope.memory_spaces else "unknown",
                duration=envelope.processing_duration,
                success=not envelope.error_state
            )
        
        # Record pipeline metrics for each transformation
        prev_timestamp = envelope.created_at
        for transformation in envelope.transformations:
            if transformation.stage.startswith("pipeline."):
                pipeline_name = transformation.stage.replace("pipeline.", "")
                # Calculate duration from previous timestamp
                duration = transformation.timestamp - prev_timestamp
                self.pipeline_metrics.record_pipeline_process(
                    pipeline=pipeline_name,
                    stage=transformation.operation,
                    duration=duration,
                    success=not transformation.metadata.get("error", False)
                )
                # Update previous timestamp for next iteration
                prev_timestamp = transformation.timestamp
        
        # Record family sync if applicable
        if envelope.family_context and envelope.family_context.get("sync_target"):
            self.memory_metrics.record_family_sync(
                source_device=envelope.device_id or "unknown",
                target_device=envelope.family_context["sync_target"],
                sync_type="memory_sync",
                duration=envelope.processing_duration,
                device_count=envelope.family_context.get("device_count", 1),
                success=not envelope.error_state
            )

# Global metrics collector instance
metrics_collector = MetricsCollector()

# Global metrics variables for easy import
pipeline_stage_duration_ms = metrics_collector.pipeline_metrics.pipeline_duration